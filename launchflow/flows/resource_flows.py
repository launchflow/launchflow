import asyncio
import dataclasses
import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple, cast

import beaupy  # type: ignore
import deepdiff  # type: ignore
import yaml
from docker.models.containers import Container  # type: ignore
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from launchflow import exceptions
from launchflow.cli.resource_utils import deduplicate_resources
from launchflow.clients.docker_client import DockerClient, docker_service_available
from launchflow.config import config
from launchflow.docker.resource import DockerResource
from launchflow.flows.flow_utils import (
    ENVIRONMENT_COLOR,
    RESOURCE_COLOR,
    SERVICE_COLOR,
    ResourceRef,
)
from launchflow.locks import Lock, LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.enums import (
    CloudProvider,
    ResourceProduct,
    ResourceStatus,
    ServiceProduct,
    ServiceStatus,
)
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
    ResourceState,
    ServiceState,
)
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.models.utils import (
    RESOURCE_PRODUCTS_TO_RESOURCES,
    SERVICE_PRODUCTS_TO_SERVICES,
)
from launchflow.node import Node
from launchflow.resource import Resource
from launchflow.service import Service
from launchflow.tofu import TofuResource
from launchflow.workflows.destroy_resource_tofu.delete_tofu_resource import (
    delete_tofu_resource,
)
from launchflow.workflows.destroy_resource_tofu.schemas import DestroyResourceTofuInputs
from launchflow.workflows.import_tofu_resource.import_tofu_resource import (
    import_tofu_resource,
)
from launchflow.workflows.import_tofu_resource.schemas import ImportResourceTofuInputs
from launchflow.workflows.manage_docker.manage_docker_resources import (
    destroy_docker_resource,
)
from launchflow.workflows.manage_docker.schemas import DestroyResourceDockerInputs


@dataclasses.dataclass
class ContainerResource:
    container: Container

    def __str__(self):
        return f'DockerContainer(name="{self.container.name}", image="{self.container.image.tags[0]}")'

    def __hash__(self) -> int:
        return hash(self.container.name)


@dataclasses.dataclass(frozen=True)
class DestroyServicePlan:
    service_name: str
    service_manager: ServiceManager
    existing_service: ServiceState

    @property
    def ref(self) -> str:
        service_cls = SERVICE_PRODUCTS_TO_SERVICES.get(
            self.existing_service.product, Service
        )
        return f"[{SERVICE_COLOR}]{service_cls.__name__}({self.service_name})[/{SERVICE_COLOR}]"


@dataclasses.dataclass(frozen=True)
class DestroyGCPServicePlan(DestroyServicePlan):
    gcp_environment_config: GCPEnvironmentConfig


@dataclasses.dataclass(frozen=True)
class DestroyAWSServicePlan(DestroyServicePlan):
    aws_environment_config: AWSEnvironmentConfig


@dataclasses.dataclass(frozen=True)
class DestroyUnknownServicePlan(DestroyServicePlan):
    pass


@dataclasses.dataclass(frozen=True)
class DestroyResourcePlan:
    resource_name: str
    resource: ResourceState
    resource_manager: ResourceManager

    @property
    def ref(self) -> str:
        resource_cls = RESOURCE_PRODUCTS_TO_RESOURCES.get(
            self.resource.product, Resource
        )
        return f"[{RESOURCE_COLOR}]{resource_cls.__name__}({self.resource_name})[/{RESOURCE_COLOR}]"


def dump_resource_inputs(resource_inputs: Dict[str, Any]):
    return yaml.safe_dump(resource_inputs).replace("'", "")


def compare_dicts(d1, d2):
    diff = deepdiff.DeepDiff(d1, d2, ignore_order=True)
    diff_keys = diff.affected_root_keys
    diff_strs = []
    for key in diff_keys:
        old_value = d1.get(key)
        new_value = d2.get(key)
        diff_strs.append(f"[cyan]{key}[/cyan]: {old_value} -> {new_value}")
    return "\n    ".join(diff_strs)


@dataclasses.dataclass
class _DestroyPlanNode:
    lock: Lock
    plan: DestroyResourcePlan
    child_plans: Dict[str, "DestroyResourcePlan"] = dataclasses.field(
        default_factory=dict
    )
    parent_plans: Dict[str, "DestroyResourcePlan"] = dataclasses.field(
        default_factory=dict
    )


async def _organize_destroy_plans(locked_plans: List[Tuple[Lock, DestroyResourcePlan]]):
    # Resources keys by the resource name they are operating on
    keyed_plans: Dict[str, _DestroyPlanNode] = {}
    root_plan_nodes: Dict[str, _DestroyPlanNode] = {}
    for lock, plan in locked_plans:
        plan_node = _DestroyPlanNode(lock, plan)
        keyed_plans[plan.resource_manager.resource_name] = plan_node
        root_plan_nodes[plan.resource_manager.resource_name] = plan_node

    # Nodes that are the root of the plan tree (i.e. they have no children)
    for plan_node in keyed_plans.values():
        if plan_node.plan.resource.depends_on:
            for resource_name in plan_node.plan.resource.depends_on:
                if resource_name not in keyed_plans:
                    continue
                child_plan = keyed_plans[resource_name]
                if resource_name in root_plan_nodes:
                    del root_plan_nodes[resource_name]
                plan_node.child_plans[resource_name] = child_plan  # type: ignore
                child_plan.parent_plans[
                    plan_node.plan.resource_manager.resource_name
                ] = plan_node  # type: ignore
    return list(root_plan_nodes.values())


def _dump_verbose_logs(logs_file: str, title: str, console: Console = Console()):
    console.print(f"───── {title} ─────")
    with open(logs_file, "r") as f:
        print(f.read())
    console.print(f"───── End of {title} ─────\n")


async def _destroy_resource(
    lock: Lock,
    plan: DestroyResourcePlan,
    environment: Optional[EnvironmentState],
    progress: Progress,
    verbose: bool,
    console: Console = Console(),
    detach: bool = False,
):
    async with lock as lock_info:
        logs_file = None
        task_description = f"Destroying {plan.ref}..."
        base_logging_dir = "/tmp/launchflow"
        os.makedirs(base_logging_dir, exist_ok=True)
        logs_file = f"{base_logging_dir}/{plan.resource.name}-{int(time.time())}.log"
        task_description += (
            f"\n  > View detailed logs with: [bold]tail -f {logs_file}[/bold]"
        )
        task = progress.add_task(task_description)

        if plan.resource.product == ResourceProduct.LOCAL_DOCKER.value:
            inputs = DestroyResourceDockerInputs(
                container_id=plan.resource_manager.get_running_container_id(),  # type: ignore
                logs_file=logs_file,
            )

            fn = destroy_docker_resource
        else:
            # EnvironmentState is not none since we load it when destroying local resources
            environment = cast(EnvironmentState, environment)

            launchflow_uri = LaunchFlowURI(
                project_name=plan.resource_manager.project_name,
                environment_name=plan.resource_manager.environment_name,
                resource_name=plan.resource_manager.resource_name,
            )
            inputs = DestroyResourceTofuInputs(  # type: ignore
                launchflow_uri=launchflow_uri,
                backend=plan.resource_manager.backend,
                lock_id=lock_info.lock_id,
                gcp_env_config=environment.gcp_config,
                aws_env_config=environment.aws_config,
                resource=plan.resource,
                logs_file=logs_file,
            )

            fn = delete_tofu_resource  # type: ignore

        plan.resource.status = ResourceStatus.DESTROYING
        # Save resource to push status update
        await plan.resource_manager.save_resource(plan.resource, lock_info.lock_id)
        try:
            if not detach:
                await fn(inputs)
            await plan.resource_manager.delete_resource(lock_info.lock_id)
            progress.remove_task(task)
            if verbose:
                _dump_verbose_logs(logs_file, f"Destroy {plan.ref} logs", console)
            progress.console.print(
                f"[green]✓[/green] {plan.ref} successfully destroyed"
            )
            success = True
        except Exception as e:
            # TODO: Log this to the logs_file
            logging.error("Exception occurred: %s", e, exc_info=True)
            plan.resource.status = ResourceStatus.DELETE_FAILED
            progress.remove_task(task)
            if verbose:
                _dump_verbose_logs(logs_file, f"Destroy {plan.ref} logs")
            progress.console.print(f"[red]✗[/red] {plan.ref} failed to delete")
            await plan.resource_manager.save_resource(plan.resource, lock_info.lock_id)
            success = False

        if not verbose:
            progress.console.print(
                f"  > View detailed logs at: [bold]{logs_file}[/bold]"
            )
        return success


async def _destroy_service(lock: Lock, plan: DestroyServicePlan, progress: Progress):
    async with lock as lock_info:
        base_logging_dir = "/tmp/launchflow"
        os.makedirs(base_logging_dir, exist_ok=True)
        logs_file = f"{base_logging_dir}/{plan.service_name}-{int(time.time())}.log"
        with open(logs_file, "a") as f:
            f.write(f"Destroying {plan.ref}...\n")
        task_description = f"Destroying {plan.ref}..."
        task_description += (
            f"\n  > View detailed logs with: [bold]tail -f {logs_file}[/bold]"
        )
        task = progress.add_task(task_description)
        plan.existing_service.status = ServiceStatus.DESTROYING
        await plan.service_manager.save_service(
            plan.existing_service, lock_info.lock_id
        )
        try:
            await plan.service_manager.delete_service(lock_info.lock_id)
            progress.console.print(f"[green]✓[/green] {plan.ref} successfully deleted")
            with open(logs_file, "a") as f:
                f.write(f"[green]✓[/green] {plan.ref} successfully deleted\n")
        except Exception as e:
            logging.error("Exception occurred: %s", e, exc_info=True)
            with open(logs_file, "a") as f:
                f.write(f"[red]✗[/red] {plan.ref} failed to delete\n")
            progress.console.print(f"[red]✗[/red] {plan.ref} failed to delete")
            plan.existing_service.status = ServiceStatus.DELETE_FAILED
            await plan.service_manager.save_service(
                plan.existing_service, lock_info.lock_id
            )

        progress.remove_task(task)
        progress.console.print(f"  > View detailed logs at: [bold]{logs_file}[/bold]")


async def destroy(
    environment_name: str,
    *nodes: Tuple[Node],
    resources_to_destroy: Set[str] = set(),
    services_to_destroy: Set[str] = set(),
    local_only: bool = False,
    prompt: bool = True,
    verbose: bool = False,
    console: Console = Console(),
    detach: bool = False,
):
    """
    Destroy resources in an environment.

    Args:
    - `environment_name`: The name of the environment to destroy.
    - `nodes`: A tuple of nodes to destroy. If none are provided, all nodes will be destroyed.
    - `resources_to_destroy`: A set of resource names to destroy. If none are provided, all resources will be destroyed.
    - `services_to_destroy`: A set of service names to destroy. If none are provided, all services will be destroyed.
    - `local_only`: Whether to destroy only local resources.
    - `prompt`: Whether to prompt the user before destroying resources.
    - `verbose`: If true all output will be written to stdout.
    - `detach`: If true, state will be deleted but no cloud resources will be touched.

    Returns:
        True if all resources were destroyed false otherwise.
    """

    environment_manager = EnvironmentManager(
        project_name=config.launchflow_yaml.project,
        environment_name=environment_name,
        backend=config.launchflow_yaml.backend,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Planning infrastructure changes...\n", total=None)

        # Stage 1. List all resources and services
        environment = None
        # TODO: refactor this logic, we shouldnt list docker resources before checking if
        # docker is available
        resources = await environment_manager.list_docker_resources()
        services = {}

        if resources and not docker_service_available():
            raise exceptions.MissingDockerDependency(
                "Docker is required to destroy local resources."
            )

        if not local_only:
            environment = await environment_manager.load_environment()
            remote_resources = await environment_manager.list_resources()
            remote_services = await environment_manager.list_services()
            # TODO: handle the case where local and remote resources share the same name
            resources.update(remote_resources)
            services.update(remote_services)

        # If nodes are provided, filter for them. If none are provided, we destroy everything
        if nodes:
            filtered_resources: Dict[str, ResourceState] = {}
            filtered_services: Dict[str, ServiceState] = {}
            loaded_resource_names = resources.keys()
            loaded_service_names = services.keys()
            for node in nodes:
                if isinstance(node, Resource):
                    if (
                        isinstance(node, DockerResource)
                        and not docker_service_available()
                    ):
                        raise exceptions.MissingDockerDependency(
                            "Docker is required to destroy local resources."
                        )

                    if node.name not in loaded_resource_names:
                        raise exceptions.ResourceNotFound(resource_name=node.name)
                    filtered_resources[node.name] = resources[node.name]
                elif isinstance(node, Service):
                    if node.name not in loaded_service_names:
                        raise exceptions.ServiceNotFound(service_name=node.name)
                    filtered_services[node.name] = services[node.name]
            resources = filtered_resources
            services = filtered_services

        if resources_to_destroy or services_to_destroy:
            if not resources_to_destroy:
                resources = {}
            else:
                resources = {
                    name: resource
                    for name, resource in resources.items()
                    if name in resources_to_destroy
                }

            if not services_to_destroy:
                services = {}
            else:
                services = {
                    name: service
                    for name, service in services.items()
                    if name in services_to_destroy
                }

        destroy_plans: List[DestroyResourcePlan] = []
        for name, resource in resources.items():
            if resource.product == ResourceProduct.LOCAL_DOCKER.value:
                resource_manager = environment_manager.create_docker_resource_manager(
                    name
                )
            else:
                resource_manager = environment_manager.create_resource_manager(name)  # type: ignore
            destroy_plans.append(
                DestroyResourcePlan(
                    resource_name=name,
                    resource=resource,
                    resource_manager=resource_manager,  # type: ignore
                )
            )
        for name, service in services.items():
            service_manager = environment_manager.create_service_manager(name)
            if service.cloud_provider == CloudProvider.GCP:
                if environment.gcp_config is None:  # type: ignore
                    raise exceptions.GCPConfigNotFound(
                        environment_name=environment_name
                    )
                destroy_plans.append(
                    DestroyGCPServicePlan(  # type: ignore
                        service_name=name,
                        service_manager=service_manager,
                        existing_service=service,
                        gcp_environment_config=environment.gcp_config,  # type: ignore
                    )
                )
            elif service.cloud_provider == CloudProvider.AWS:
                if environment.aws_config is None:  # type: ignore
                    raise exceptions.AWSConfigNotFound(
                        environment_name=environment_name
                    )
                destroy_plans.append(
                    DestroyAWSServicePlan(  # type: ignore
                        service_name=name,
                        service_manager=service_manager,
                        existing_service=service,
                        aws_environment_config=environment.aws_config,  # type: ignore
                    )
                )
            elif service.product == ServiceProduct.UNKNOWN:
                destroy_plans.append(
                    DestroyUnknownServicePlan(  # type: ignore
                        service_name=name,
                        service_manager=service_manager,
                        existing_service=service,
                    )
                )
            else:
                raise NotImplementedError(
                    f"Service product {service.product} is not supported"
                )

        progress.remove_task(task)

    if not destroy_plans:
        console.print(
            "[green]No resources or services to delete in the environment.[/green]\n"
        )
        console.print(
            f"[yellow]NOTE[/yellow] You can run [blue]`lf environments delete {environment_name}`[/blue] to delete the environment."
        )
        return True

    # Stage 2. Confirm the deletions
    if not prompt:
        selected_plans = destroy_plans
    else:
        # Sort the plans to make it easier to grok for the user.
        destroy_plans.sort(key=lambda plan: plan.ref)
        console.print(
            f"Select the resources / services you want to delete in [{ENVIRONMENT_COLOR}]`{environment_name}`[/{ENVIRONMENT_COLOR}]."
        )
        selected_plans = beaupy.select_multiple(
            options=destroy_plans,
            preprocessor=lambda plan: plan.ref,
            page_size=10,
            pagination=True,
        )
        for plan in selected_plans:
            console.print(f"[[pink1]✓[/pink1]] [pink1]{plan.ref}[/pink1]")
        print()

        if selected_plans:
            console.print("[bold yellow]Destroying:[/bold yellow]")
            for plan in selected_plans:
                console.print(f"- [pink1]{plan.ref}[/pink1]")
            confirmation = beaupy.confirm(
                "Destroy these resources? This cannot be undone.",
                default_is_yes=True,
            )
            if not confirmation:
                console.print("Canceled, exiting.")
                return
    if not selected_plans:
        console.print("No resources / services selected. Exiting.")
        return True

    service_plans_to_execute = []
    resource_plans_to_execute = []
    selected_remote_plans = []

    for plan in selected_plans:
        # Lock local resources withouth the environment
        # this prevents the need for credentials to the artifact
        # bucket if you are only destroying local resources
        if (
            isinstance(plan, DestroyResourcePlan)
            and plan.resource.product == ResourceProduct.LOCAL_DOCKER.value
        ):
            lock = await plan.resource_manager.lock_resource(
                operation=LockOperation(operation_type=OperationType.DESTROY_RESOURCE)
            )
            resource_plans_to_execute.append((lock, plan))
        else:
            selected_remote_plans.append(plan)
    if selected_remote_plans:
        async with await environment_manager.lock_environment(
            operation=LockOperation(operation_type=OperationType.LOCK_ENVIRONMENT)
        ):
            for plan in selected_remote_plans:
                if isinstance(plan, DestroyServicePlan):
                    lock = await plan.service_manager.lock_service(
                        operation=LockOperation(
                            operation_type=OperationType.DESTROY_SERVICE
                        )
                    )
                    service_plans_to_execute.append((lock, plan))
                else:
                    lock = await plan.resource_manager.lock_resource(
                        operation=LockOperation(
                            operation_type=OperationType.DESTROY_RESOURCE
                        )
                    )
                    resource_plans_to_execute.append((lock, plan))

    organize_plans = await _organize_destroy_plans(resource_plans_to_execute)
    # Stage 3. Destroy the resources
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        pending = set()
        plans_to_start: List[_DestroyPlanNode] = organize_plans
        completed_plans: Dict[str, _DestroyPlanNode] = {}

        for lock, plan in service_plans_to_execute:
            pending.add(asyncio.create_task(_destroy_service(lock, plan, progress)))

        while pending or plans_to_start:
            while plans_to_start:
                plan_node = plans_to_start.pop(0)

                async def execute_plan_wrapper(node):
                    result = await _destroy_resource(
                        node.lock,
                        node.plan,
                        environment,
                        progress,
                        verbose,
                        console,
                        detach,
                    )
                    results.append(result)
                    completed_plans[node.plan.resource_manager.resource_name] = node
                    for child_plan in node.child_plans.values():
                        if all(
                            parent in completed_plans
                            for parent in child_plan.parent_plans.keys()
                        ):
                            plans_to_start.append(child_plan)

                pending.add(asyncio.create_task(execute_plan_wrapper(plan_node)))

            _, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
    return all(results)


async def stop_local_containers(
    container_ids: List[str],
    prompt: bool = True,
    console: Console = Console(),
):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task(
            "Loading local resources",
        )
        containers = []
        if docker_service_available():
            _client = DockerClient()
            containers = [
                ContainerResource(_client.get_container(container_id))
                for container_id in container_ids
            ]
        to_stop_options = [
            container
            for container in containers
            if container.container.status == "running"
        ]
        progress.remove_task(task)

    to_stop = set()
    if not to_stop_options:
        progress.console.print(
            "[green]✓[/green] No containers to stop. No action required."
        )
        return
    if prompt:
        console.print(
            "The following running local containers were found. Select which you would like to [bold]stop[/bold]:"
        )
        options = [
            f"[bold]Stop[/bold]: [bold]{container}[/bold]"
            for container in to_stop_options
        ]
        answers = beaupy.select_multiple(options, return_indices=True)
        for answer in answers:
            console.print(
                f"[pink1]>[/pink1] Stop: [{RESOURCE_COLOR}]{to_stop_options[answer]}[/{RESOURCE_COLOR}]"
            )
            to_stop.add(to_stop_options[answer])
        if not to_stop:
            console.print(
                "[green]✓[/green] No containers selected. No action required."
            )
            return
    else:
        for container in to_stop_options:
            to_stop.add(container)

    docker_client = None
    stop_queue = set()
    for container in to_stop:
        task = progress.add_task(
            f"Stopping [{RESOURCE_COLOR}]{container}[/{RESOURCE_COLOR}]...", total=1
        )

        if docker_client is None:
            docker_client = DockerClient()
        docker_client.stop_container(container.container.name)

        stop_queue.add((container, task))

    successes = 0
    failures = 0
    while stop_queue:
        await asyncio.sleep(0.5)

        while stop_queue:
            container, task = stop_queue.pop()
            try:
                container.container.reload()
                if container.container.status == "exited":
                    progress.console.print(
                        f"[green]✓[/green] Stop successful for [{RESOURCE_COLOR}]{container}[/{RESOURCE_COLOR}]"
                    )
                    successes += 1
            except Exception as e:
                progress.remove_task(task)
                progress.console.print(f"[red]✗[/red] Failed to stop {container}")
                progress.console.print(f"    └── {e}")
                failures += 1
            finally:
                progress.remove_task(task)

    if successes:
        progress.console.print(
            f"[green]✓[/green] Successfully stopped {successes} containers"
        )
    if failures:
        progress.console.print(f"[red]✗[/red] Failed to stop {failures} containers")


@dataclasses.dataclass
class ImportResourcePlan:
    resource: TofuResource
    resource_manager: ResourceManager
    import_inputs: Optional[Dict[str, str]] = dataclasses.field(
        default_factory=dict, init=False
    )

    @property
    def ref(self):
        return ResourceRef(self.resource)


async def _run_import_plans(
    environment_state: EnvironmentState,
    plan: ImportResourcePlan,
    progress: Progress,
):
    if plan.import_inputs is None:
        raise ValueError("Import inputs must be provided to import a resource")
    base_logging_dir = "/tmp/launchflow"
    os.makedirs(base_logging_dir, exist_ok=True)
    logs_file = f"{base_logging_dir}/{plan.resource.name}-{int(time.time())}.log"
    task_description = f"Importing {plan.ref}..."
    task_description += (
        f"\n  > View detailed logs with: [bold]tail -f {logs_file}[/bold]"
    )
    task = progress.add_task(task_description)
    launchflow_uri = LaunchFlowURI(
        project_name=plan.resource_manager.project_name,
        environment_name=plan.resource_manager.environment_name,
        resource_name=plan.resource_manager.resource_name,
    )
    updated_time = datetime.datetime.now(datetime.timezone.utc)
    created_time = updated_time
    status = ResourceStatus.CREATING
    new_resource_state = ResourceState(
        name=plan.resource.name,
        product=plan.resource.product,
        cloud_provider=plan.resource.cloud_provider(),
        created_at=created_time,
        updated_at=updated_time,
        status=status,
        inputs=plan.resource.inputs(environment_state).to_dict(),
        depends_on=[r.name for r in plan.resource.inputs_depend_on(environment_state)],
    )
    to_save = None
    async with await plan.resource_manager.lock_resource(
        LockOperation(operation_type=OperationType.IMPORT_RESOURCE)
    ) as lock:
        try:
            imports = plan.import_inputs

            inputs = ImportResourceTofuInputs(
                resource_id=plan.resource.resource_id,
                launchflow_uri=launchflow_uri,
                backend=plan.resource_manager.backend,
                gcp_env_config=environment_state.gcp_config,
                aws_env_config=environment_state.aws_config,
                resource=new_resource_state,
                imports=imports,
                lock_id=lock.lock_id,
                logs_file=logs_file,
            )
            to_save = new_resource_state.model_copy()
            outputs = await import_tofu_resource(inputs)
            to_save.aws_arn = outputs.aws_arn
            to_save.gcp_id = outputs.gcp_id
            to_save.status = ResourceStatus.READY
            message = f"[green]✓[/green] Successfully imported {plan.ref}"
            await plan.resource_manager.save_resource(to_save, lock.lock_id)

        except Exception as e:
            # TODO: Log this to the logs_file
            logging.error("Exception occurred: %s", e, exc_info=True)
            # This can be none if we failed to call `import_resource`
            if to_save is not None:
                # Reset the create args to their original state
                to_save.inputs = None
                to_save.status = ResourceStatus.CREATE_FAILED
            message = f"[red]✗[/red] Failed to import {plan.ref}"
            message += f"\n  > {e}"
            # We delete the resource here since it failed to import
            await plan.resource_manager.delete_resource(lock.lock_id)

    progress.remove_task(task)
    message += f"\n  > View detailed logs at: [bold]{logs_file}[/bold]"
    progress.console.print(message)


# TODO: add locks here
async def import_existing_resources(
    environment_name: str, *resources: Tuple[Resource], console: Console = Console()
):
    resources: List[Resource] = deduplicate_resources(resources)  # type: ignore

    environment_manager = EnvironmentManager(
        project_name=config.launchflow_yaml.project,
        environment_name=environment_name,
        backend=config.launchflow_yaml.backend,
    )
    environment = await environment_manager.load_environment()

    plans = []
    for resource in resources:
        rm = environment_manager.create_resource_manager(resource.name)  # type: ignore
        try:
            resource_state = await rm.load_resource()
            if resource_state.status == ResourceStatus.CREATE_FAILED:
                plans.append(ImportResourcePlan(resource=resource, resource_manager=rm))  # type: ignore
        except exceptions.ResourceNotFound:
            plans.append(ImportResourcePlan(resource=resource, resource_manager=rm))  # type: ignore

    environment_ref = (
        f"{environment_manager.project_name}/{environment_manager.environment_name}"
    )
    console.print(
        f"Select the resources you want to imports in [bold yellow]`{environment_ref}`[/bold yellow]:"
    )
    selected_plans: List[ImportResourcePlan] = beaupy.select_multiple(
        options=plans,
        preprocessor=lambda plan: f"[bold]Import[/bold] {plan.resource.__class__.__name__}({plan.resource.name})",
    )
    for plan in selected_plans:
        console.print(
            f"[[pink1]✓[/pink1]] [pink1]{plan.resource.__class__.__name__}({plan.resource.name})[/pink1]"
        )
        plan.import_inputs = plan.resource.import_tofu_resource(environment)

    tasks = []
    print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        for plan in selected_plans:
            tasks.append(
                asyncio.create_task(_run_import_plans(environment, plan, progress))
            )
        await asyncio.gather(*tasks)
