import asyncio
import dataclasses
import datetime
import io
import os
import time
from functools import cached_property
from typing import Dict, List, Literal, Optional, Tuple, Union

import deepdiff  # type: ignore
import rich
from rich.console import Console
from rich.live import Live
from rich.padding import Padding
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.table import Table
from rich.tree import Tree

import launchflow
from launchflow import exceptions
from launchflow.cli.resource_utils import is_secret_resource
from launchflow.clients.docker_client import docker_service_available
from launchflow.config import config
from launchflow.docker.resource import DockerResource
from launchflow.flows.flow_utils import (
    OP_COLOR,
    ResourceRef,
    ServiceRef,
    compare_dicts,
    dump_verbose_logs,
    format_configuration_dict,
)
from launchflow.flows.plan import (
    FailedToPlan,
    FlowResult,
    ResourcePlan,
    Result,
    ServicePlan,
    execute_plans,
)
from launchflow.flows.plan_utils import lock_plans, print_plans, select_plans
from launchflow.locks import Lock, LockOperation, OperationType, ReleaseReason
from launchflow.logger import logger
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.enums import (
    CloudProvider,
    EnvironmentStatus,
    ResourceProduct,
    ResourceStatus,
    ServiceProduct,
    ServiceStatus,
)
from launchflow.models.flow_state import EnvironmentState, ResourceState, ServiceState
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Node
from launchflow.resource import Resource
from launchflow.service import DNSOutputs, Service
from launchflow.tofu import TofuResource
from launchflow.validation import validate_resource_name, validate_service_name
from launchflow.workflows.apply_resource_tofu.create_tofu_resource import (
    create_tofu_resource,
)
from launchflow.workflows.manage_docker.manage_docker_resources import (
    create_docker_resource,
    replace_docker_resource,
)
from launchflow.workflows.manage_docker.schemas import CreateResourceDockerInputs


@dataclasses.dataclass
class CreateResourceResult(Result["CreateResourcePlan"]):
    resource_state: ResourceState
    logs_file: Optional[str] = None


@dataclasses.dataclass
class CreateResourcePlan(ResourcePlan):
    resource_manager: ResourceManager
    existing_resource_state: Optional[ResourceState]
    environment_state: EnvironmentState
    _lock: Optional[Lock] = None

    def __str__(self):
        if self.operation_type == "noop":
            return f"Create {ResourceRef(self.resource_or_service)}"  # type: ignore
        return f"{self.operation_type.title()} {ResourceRef(self.resource_or_service)}"  # type: ignore

    # TODO: this would be better if it was encapsulated in the resource inputs
    @cached_property
    def _new_resource_inputs(self):
        new_inputs = self.resource.inputs(self.environment_state).to_dict()
        if (
            self.existing_resource_state is None
            or self.existing_resource_state.inputs is None
        ):
            return new_inputs
        new_root = new_inputs
        old_root = self.existing_resource_state.inputs
        for key in self.resource.ignore_arguments:
            split = key.split(".")
            for part in split[:-1]:
                new_root = new_root[part]
                old_root = old_root[part]
            new_root[split[-1]] = old_root[split[-1]]
        return new_inputs

    @cached_property
    def operation_type(self) -> Literal["noop", "create", "update", "replace"]:
        operation_type = "noop"
        if (
            self.existing_resource_state is None
            or self.existing_resource_state.status == ResourceStatus.CREATE_FAILED
        ):
            return "create"
        existing_resource_inputs = {}
        if self.existing_resource_state is not None:
            existing_resource_inputs = self.existing_resource_state.inputs or {}
        new_resource_inputs = self._new_resource_inputs
        resource_diff = deepdiff.DeepDiff(
            existing_resource_inputs,
            new_resource_inputs,
            ignore_order=True,
        )
        if resource_diff.affected_root_keys:
            operation_type = "update"
            for key in resource_diff.affected_root_keys:
                if key in self.resource.replacement_arguments:
                    operation_type = "replace"
                    break
        return operation_type  # type: ignore

    async def abandon_plan(self, reason: str):
        if self._lock is not None:
            await self._lock.release(ReleaseReason.ABANDONED)

        result = CreateResourceResult(
            plan=self,
            success=False,
            resource_state=self.existing_resource_state,  # type: ignore
            logs_file=None,
        )
        result.error_message = f"Create abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> CreateResourceResult:
        if self._lock is None:
            return await self.abandon_plan("Plan was not locked before execution.")

        # SETUP
        base_logging_dir = "/tmp/launchflow"
        os.makedirs(base_logging_dir, exist_ok=True)
        logs_file = f"{base_logging_dir}/{self.resource.name}-{int(time.time())}.log"

        launchflow_uri = LaunchFlowURI(
            project_name=self.resource_manager.project_name,
            environment_name=self.resource_manager.environment_name,
            resource_name=self.resource_manager.resource_name,
        )

        # BEGIN EXECUTION
        async with self._lock as lock_info:
            updated_time = datetime.datetime.now(datetime.timezone.utc)
            if self.existing_resource_state:
                created_time = self.existing_resource_state.created_at
                inputs = self.existing_resource_state.inputs
                depends_on = self.existing_resource_state.depends_on
                gcp_id = self.existing_resource_state.gcp_id
                aws_arn = self.existing_resource_state.aws_arn
            else:
                created_time = updated_time
                # NOTE: We dont save the inputs until the create is successful
                inputs = None
                # NOTE: We dont save the depends_on until the create is successful
                depends_on = []
                gcp_id = None
                aws_arn = None

            if self.operation_type == "update":
                status = ResourceStatus.UPDATING
            elif self.operation_type == "replace":
                status = ResourceStatus.REPLACING
            else:
                status = ResourceStatus.CREATING

            new_resource_state = ResourceState(
                name=self.resource.name,
                product=self.resource.product,
                cloud_provider=self.resource.cloud_provider(),
                created_at=created_time,
                updated_at=updated_time,
                status=status,
                inputs=inputs,
                depends_on=depends_on,
                gcp_id=gcp_id,
                aws_arn=aws_arn,
            )

            # Handle all exceptions to ensure we commit the service state properly
            try:
                # Save intermediate resource state to push status to the backend
                await self.resource_manager.save_resource(
                    new_resource_state, lock_info.lock_id
                )

                # NOTE: We make a copy of the resource state since we dont want to
                # save the inputs or depends_on until the create is successful.
                # This copy should only be used until we refactor the create docker
                # and tofu functions below
                resource_state_copy = new_resource_state.model_copy(deep=True)
                resource_state_copy.inputs = self._new_resource_inputs
                # TODO: Dependencies are not always set correctly. See Lambda's
                # dependency on API Gateway for example
                resource_state_copy.depends_on = [
                    dep.name
                    for dep in self.resource.inputs_depend_on(self.environment_state)
                ]

                final_inputs = self.resource.execute_inputs(
                    self.environment_state
                ).to_dict()

                if isinstance(self.resource, DockerResource):
                    await _create_or_update_docker_resource(
                        self, resource_state_copy, self.operation_type, logs_file
                    )
                    gcp_id = None
                    aws_arn = None
                elif isinstance(self.resource, TofuResource):
                    tofu_outputs = await create_tofu_resource(
                        tofu_resource=self.resource,
                        environment_state=self.environment_state,
                        backend=self.resource_manager.backend,
                        launchflow_uri=launchflow_uri,
                        lock_id=lock_info.lock_id,
                        logs_file=logs_file,
                    )
                    gcp_id = tofu_outputs.gcp_id
                    aws_arn = tofu_outputs.aws_arn
                else:
                    raise NotImplementedError(
                        f"Resource type {self.resource.__class__.__name__} is not supported."
                    )

                new_resource_state.status = ResourceStatus.READY
                new_resource_state.aws_arn = aws_arn
                new_resource_state.gcp_id = gcp_id
                # NOTE: We save the inputs only if the create was successful
                new_resource_state.inputs = final_inputs

                # NOTE: We save the depends_on only if the create was successful
                new_resource_state.depends_on = [
                    dep.name
                    for dep in self.resource.dependencies(self.environment_state)
                ]

                await self.resource_manager.save_resource(
                    new_resource_state, lock_info.lock_id
                )

                if self.verbose:
                    dump_verbose_logs(
                        logs_file,
                        f"Create {self.resource.__class__.__name__}({self.resource.name}) logs",
                    )
                new_resource_state.attempted_inputs = None

                return CreateResourceResult(
                    plan=self,
                    success=True,
                    resource_state=new_resource_state,
                    logs_file=logs_file,
                )
            except Exception as e:
                logger.debug(
                    "Exception occurred while creating resource %s: %s",
                    self.resource.name,
                    e,
                    exc_info=True,
                )
                # If an exception occurs we save the resource state with a failed status
                if new_resource_state.status == ResourceStatus.CREATING:
                    new_resource_state.status = ResourceStatus.CREATE_FAILED
                elif new_resource_state.status == ResourceStatus.REPLACING:
                    new_resource_state.status = ResourceStatus.REPLACE_FAILED
                else:
                    new_resource_state.status = ResourceStatus.UPDATE_FAILED
                # If it failed we record what inputs were used
                new_resource_state.attempted_inputs = final_inputs
                await self.resource_manager.save_resource(
                    new_resource_state, lock_info.lock_id
                )
                result = CreateResourceResult(
                    plan=self,
                    success=False,
                    resource_state=new_resource_state,
                    logs_file=logs_file,
                )
                result.error_message = str(e)
                return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        left_padding_str = " " * left_padding
        resource_inputs = self._new_resource_inputs
        if self.existing_resource_state is None or (
            self.existing_resource_state.inputs is None
            and self.existing_resource_state.status == ResourceStatus.CREATE_FAILED
        ):
            if resource_inputs:
                resource_inputs_str = format_configuration_dict(resource_inputs)
                console.print(
                    f"{left_padding_str}{ResourceRef(self.resource)} will be [{OP_COLOR}]created[/{OP_COLOR}] with the following configuration:"
                )
                console.print(
                    left_padding_str
                    + "    "
                    + f"\n{left_padding_str}    ".join(resource_inputs_str.split("\n"))
                )
            else:
                # TODO: Print the default configuration instead of this message
                console.print(
                    f"{left_padding_str}{ResourceRef(self.resource)} will be [{OP_COLOR}]created[/{OP_COLOR}] with the default configuration."
                )
                console.print()
        else:
            args_diff = compare_dicts(
                self.existing_resource_state.inputs or {},
                resource_inputs,
            )
            if args_diff:
                op_msg = "updated"
                if self.operation_type == "replace":
                    op_msg = "replaced"
                console.print(
                    f"{left_padding_str}{ResourceRef(self.resource)} will be [{OP_COLOR}]{op_msg}[/{OP_COLOR}] with the following updates:"
                )
                console.print(
                    left_padding_str
                    + f"\n{left_padding_str}".join(args_diff.split("\n"))
                )
            console.print()

    def pending_message(self):
        if self.operation_type == "create":
            return f"Create {ResourceRef(self.resource)} waiting for dependencies..."
        if self.operation_type == "update":
            return f"Update {ResourceRef(self.resource)} waiting for dependencies..."
        if self.operation_type == "replace":
            return f"Replace {ResourceRef(self.resource)} waiting for dependencies..."
        return f"Unknown operation on {ResourceRef(self.resource)} waiting for dependencies..."

    def task_message(self):
        if self.operation_type == "create":
            return f"Creating {ResourceRef(self.resource)}..."
        if self.operation_type == "update":
            return f"Updating {ResourceRef(self.resource)}..."
        if self.operation_type == "replace":
            return f"Replacing {ResourceRef(self.resource)}..."
        return f"Running unknown operation for {ResourceRef(self.resource)}..."

    def success_message(self):
        if self.operation_type == "create":
            return f"Successfully created {ResourceRef(self.resource)}"
        if self.operation_type == "update":
            return f"Successfully updated {ResourceRef(self.resource)}"
        if self.operation_type == "replace":
            return f"Successfully replaced {ResourceRef(self.resource)}"
        return f"Successfully ran unknown operation for {ResourceRef(self.resource)}"

    def failure_message(self):
        return f"Failed to {self.operation_type} {ResourceRef(self.resource)}"

    async def lock_plan(self) -> Optional[Lock]:
        if self.operation_type == "noop":
            return None
        if self._lock is not None:
            raise exceptions.PlanAlreadyLocked(self)

        op_type = OperationType.CREATE_RESOURCE
        if self.operation_type == "update":
            op_type = OperationType.UPDATE_RESOURCE
        elif self.operation_type == "replace":
            op_type = OperationType.REPLACE_RESOURCE
        plan_output = io.StringIO()
        console = Console(no_color=True, file=plan_output)
        self.print_plan(console)
        plan_output.seek(0)

        lock = await self.resource_manager.lock_resource(
            operation=LockOperation(
                operation_type=op_type, metadata={"plan": plan_output.read()}
            ),
        )

        try:
            refreshed_resource_state = await self.resource_manager.load_resource()
        except exceptions.ResourceNotFound:
            refreshed_resource_state = None

        def _resource_state_differs(
            existing: Optional[ResourceState], refreshed: Optional[ResourceState]
        ) -> bool:
            if existing is None:
                if (
                    refreshed is not None
                    and refreshed.product != ResourceProduct.UNKNOWN.value
                ):
                    return True
                return False
            return existing != refreshed

        if _resource_state_differs(
            self.existing_resource_state, refreshed_resource_state
        ):
            # If the resource has changed since planning we release the lock
            # and will not attempt to execute the plan
            await lock.release(reason=ReleaseReason.ABANDONED)
            raise exceptions.ResourceStateMismatch(self.resource)

        self._lock = lock
        return lock


@dataclasses.dataclass
class CreateServiceResult(Result["CreateServicePlan"]):
    service_state: ServiceState
    create_resource_results: List[CreateResourceResult]
    dns_outputs: Optional[DNSOutputs]


@dataclasses.dataclass
class CreateServicePlan(ServicePlan):
    service_manager: ServiceManager
    existing_service_state: Optional[ServiceState]
    environment_state: EnvironmentState
    create_resource_plans: List[CreateResourcePlan]
    _lock: Optional[Lock] = None

    def __str__(self):
        if self.operation_type == "noop":
            return f"Create {ServiceRef(self.resource_or_service)}"  # type: ignore
        return f"{self.operation_type.title()} {ServiceRef(self.resource_or_service)}"  # type: ignore

    @cached_property
    def operation_type(self) -> Literal["noop", "create", "update"]:
        operation_type = "noop"
        if (
            self.existing_service_state is None
            or self.existing_service_state.status == ServiceStatus.CREATE_FAILED
        ):
            return "create"
        for resource_plan in self.create_resource_plans:
            if resource_plan.operation_type == "create":
                operation_type = "create"
            elif (
                resource_plan.operation_type == "replace"
                or resource_plan.operation_type == "update"
            ):
                operation_type = "update"
                break
        return operation_type  # type: ignore

    def child_plans(self) -> List[CreateResourcePlan]:  # type: ignore
        return self.create_resource_plans

    async def abandon_plan(self, reason: str):
        if self._lock is not None:
            await self._lock.release(ReleaseReason.ABANDONED)

        result = CreateServiceResult(
            plan=self,
            success=False,
            service_state=self.existing_service_state,  # type: ignore
            create_resource_results=[],
            dns_outputs=None,
        )
        result.error_message = f"Create abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> CreateServiceResult:
        if self._lock is None:
            return await self.abandon_plan("Plan was not locked before execution.")

        async with self._lock as lock_info:
            updated_time = datetime.datetime.now(datetime.timezone.utc)
            if self.existing_service_state:
                created_time = self.existing_service_state.created_at
                inputs = self.existing_service_state.inputs
                gcp_id = self.existing_service_state.gcp_id
                aws_arn = self.existing_service_state.aws_arn
                service_url = self.existing_service_state.service_url
                docker_image = self.existing_service_state.docker_image
            else:
                created_time = updated_time
                # NOTE: We dont save the inputs until the create is successful
                inputs = None
                gcp_id = None
                aws_arn = None
                service_url = None
                docker_image = None

            if self.operation_type == "update":
                status = ServiceStatus.UPDATING
            else:
                status = ServiceStatus.CREATING

            new_service_state = ServiceState(
                name=self.service.name,
                product=self.service.product,
                cloud_provider=self.service.cloud_provider(),
                created_at=created_time,
                updated_at=updated_time,
                status=status,
                inputs=inputs,
                gcp_id=gcp_id,
                aws_arn=aws_arn,
                service_url=service_url,
                docker_image=docker_image,
            )

            non_noop_plans = [
                plan
                for plan in self.create_resource_plans
                if plan.operation_type != "noop"
            ]

            # Handle all exceptions to ensure we commit the service state properly
            try:
                # Save intermediate service state to push status to the backend
                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )

                create_resource_results: List[
                    CreateResourceResult
                ] = await execute_plans(  # type: ignore
                    non_noop_plans,  # type: ignore
                    tree,  # type: ignore
                )  # type: ignore

                create_successful = all(
                    result.success for result in create_resource_results
                )
                service_outputs = None
                if create_successful:
                    # NOTE: This will fetch outputs from the underlying resources we
                    # just created
                    service_outputs = self.service.outputs()
                    new_service_state.status = ServiceStatus.READY
                    new_service_state.aws_arn = service_outputs.aws_arn
                    new_service_state.gcp_id = service_outputs.gcp_id
                    new_service_state.service_url = service_outputs.service_url
                    # NOTE: We save the inputs only if the create was successful
                    new_service_state.inputs = self.service.inputs().to_dict()
                else:
                    if new_service_state.status == ServiceStatus.CREATING:
                        new_service_state.status = ServiceStatus.CREATE_FAILED
                    else:
                        new_service_state.status = ServiceStatus.UPDATE_FAILED

                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )

                return CreateServiceResult(
                    plan=self,
                    success=create_successful,
                    service_state=new_service_state,
                    create_resource_results=create_resource_results,
                    dns_outputs=(
                        service_outputs.dns_outputs
                        if service_outputs is not None
                        else None
                    ),
                )
            except Exception as e:
                logger.debug(
                    "Exception occurred while creating service %s:\n%s %s",
                    self.service.name,
                    type(e).__name__,
                    e,
                    exc_info=True,
                )
                # If an exception occurs we save the service state with a failed status
                if new_service_state.status == ServiceStatus.CREATING:
                    new_service_state.status = ServiceStatus.CREATE_FAILED
                else:
                    new_service_state.status = ServiceStatus.UPDATE_FAILED
                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )
                create_resource_results = asyncio.gather(  # type: ignore
                    *[
                        resource_plan.abandon_plan(
                            "Unknown error occurred while creating service."
                        )
                        for resource_plan in non_noop_plans
                    ]
                )
                result = CreateServiceResult(
                    plan=self,
                    success=False,
                    service_state=new_service_state,
                    create_resource_results=create_resource_results,
                    dns_outputs=None,
                )
                result.error_message = str(e)
                return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        left_padding_str = " " * left_padding
        if self.existing_service_state is None or (
            self.existing_service_state.status == ServiceStatus.CREATE_FAILED
        ):
            all_noop_plans = all(
                resource_plan.operation_type == "noop"
                for resource_plan in self.create_resource_plans
            )
            if all_noop_plans:
                console.print(
                    f"{left_padding_str}{ServiceRef(self.service)} will be [{OP_COLOR}]created[/{OP_COLOR}], but no resources need to be created.\n"
                )
            else:
                console.print(
                    f"{left_padding_str}{ServiceRef(self.service)} will be [{OP_COLOR}]created[/{OP_COLOR}] with the following Resources:"
                )
                for resource_plan in self.create_resource_plans:
                    if resource_plan.operation_type == "noop":
                        continue
                    resource_plan.print_plan(console, left_padding=left_padding + 4)

        else:
            op_msg = "created"
            if self.operation_type == "update":
                op_msg = "updated"
            console.print(
                f"{ServiceRef(self.service)} will be [{OP_COLOR}]{op_msg}[/{OP_COLOR}] with the following Resource updates:\n"
            )
            for resource_plan in self.create_resource_plans:
                if resource_plan.operation_type == "noop":
                    continue
                resource_plan.print_plan(console, left_padding=left_padding + 4)
            console.print()

    def pending_message(self):
        if self.operation_type == "create":
            return f"Create {ServiceRef(self.service)} waiting for dependencies..."
        if self.operation_type == "update":
            return f"Update {ServiceRef(self.service)} waiting for dependencies..."
        return f"Unknown operation on {ServiceRef(self.service)} waiting for dependencies..."

    def task_message(self):
        if self.operation_type == "create":
            return f"Creating {ServiceRef(self.service)}..."
        if self.operation_type == "update":
            return f"Updating {ServiceRef(self.service)}..."
        return f"Running unknown operation for {ServiceRef(self.service)}..."

    def success_message(self):
        if self.operation_type == "create":
            return f"Successfully created {ServiceRef(self.service)}"
        if self.operation_type == "update":
            return f"Successfully updated {ServiceRef(self.service)}"
        return f"Successfully ran unknown operation for {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to {self.operation_type} {ServiceRef(self.service)}"

    async def lock_plan(self) -> Lock:
        if self._lock is not None:
            raise exceptions.PlanAlreadyLocked(self)

        op_type = OperationType.CREATE_SERVICE
        if self.operation_type == "update":
            op_type = OperationType.UPDATE_SERVICE
        plan_output = io.StringIO()
        console = Console(no_color=True, file=plan_output)
        self.print_plan(console)
        plan_output.seek(0)

        lock = await self.service_manager.lock_service(
            operation=LockOperation(
                operation_type=op_type, metadata={"plan": plan_output.read()}
            ),
        )

        try:
            refreshed_service_state = await self.service_manager.load_service()
        except exceptions.ServiceNotFound:
            refreshed_service_state = None

        def service_states_differ(
            existing: Optional[ServiceState], refreshed: Optional[ServiceState]
        ):
            # 1. new service where existiing service state is null and refreshed maybe null or unknown
            if existing is None:
                if (
                    refreshed is not None
                    and refreshed.product != ServiceProduct.UNKNOWN
                ):
                    return True
                return False
            else:
                return self.existing_service_state != refreshed_service_state

        if service_states_differ(self.existing_service_state, refreshed_service_state):
            # If the service has changed since planning we release the lock
            # and will not attempt to execute the plan
            await lock.release(reason=ReleaseReason.ABANDONED)
            raise exceptions.ServiceStateMismatch(self.service)

        self._lock = lock
        return lock


async def _create_or_update_docker_resource(
    plan: CreateResourcePlan,
    new_resource_state: ResourceState,
    operation_type: str,
    logs_file: str,
):
    resource: DockerResource = plan.resource  # type: ignore

    inputs = CreateResourceDockerInputs(
        resource=new_resource_state,
        image=resource.docker_image,
        env_vars=resource.env_vars,
        command=resource.command,  # type: ignore
        ports=resource.ports,
        logs_file=logs_file,
        environment_name=plan.resource_manager.environment_name,
        resource_inputs=resource.inputs().to_dict(),
    )

    if operation_type == "create":
        outputs = await create_docker_resource(inputs)
    elif operation_type == "update":
        outputs = await replace_docker_resource(inputs)
    else:
        raise NotImplementedError(f"Got an unexpected operator type {operation_type}.")

    resource.ports.update(outputs.ports)
    resource.running_container_id = outputs.container.id


async def plan_create_resource(
    resource: Resource,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
) -> Union[CreateResourcePlan, FailedToPlan]:
    try:
        validate_resource_name(resource.name)
    except exceptions.InvalidResourceName as e:
        return FailedToPlan(
            resource=resource,
            error_message=str(e),
        )

    if resource.cloud_provider() == CloudProvider.GCP:
        if environment_state.gcp_config is None:
            return FailedToPlan(
                resource=resource,
                error_message="CloudProviderMismatch: Cannot use a GCP Resource in an AWS Environment.",
            )
    elif resource.cloud_provider() == CloudProvider.AWS:
        if environment_state.aws_config is None:
            return FailedToPlan(
                resource=resource,
                error_message="CloudProviderMismatch: Cannot use an AWS Resource in a GCP Environment.",
            )
    elif isinstance(resource, DockerResource):
        if not docker_service_available():
            return FailedToPlan(
                resource=resource,
                error_message="DockerServiceUnavailable: Cannot create Docker resources without Docker service available.",
            )

    if isinstance(resource, DockerResource):
        resource_manager = environment_manager.create_docker_resource_manager(
            resource.name
        )
    else:
        resource_manager = environment_manager.create_resource_manager(resource.name)  # type: ignore
    try:
        existing_resource_state = await resource_manager.load_resource()
    except exceptions.ResourceNotFound:
        existing_resource_state = None

    if existing_resource_state is not None:
        if (
            existing_resource_state.product != resource.product
            and existing_resource_state.product != ResourceProduct.UNKNOWN
        ):
            exception = exceptions.ResourceProductMismatch(
                resource=resource,
                existing_product=existing_resource_state.product,
                new_product=resource.product,
            )
            return FailedToPlan(
                resource=resource,
                error_message=str(exception),
            )
        if existing_resource_state.status.is_pending():
            return FailedToPlan(
                resource=resource,
                error_message=f"ResourcePending: Cannot create a resource that is already pending. Current status: {existing_resource_state.status}",
            )

    # Return the plan
    return CreateResourcePlan(
        resource_or_service=resource,
        resource_manager=resource_manager,  # type: ignore
        existing_resource_state=existing_resource_state,
        environment_state=environment_state,
        depends_on=[],
        verbose=verbose,
    )


async def plan_create_resources(
    *resources: Resource,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
    parent_resource_plans: Dict[str, CreateResourcePlan] = {},
) -> List[Union[CreateResourcePlan, FailedToPlan]]:
    plan_tasks = []
    for resource in resources:
        plan_tasks.append(
            plan_create_resource(
                resource=resource,
                environment_state=environment_state,
                environment_manager=environment_manager,
                verbose=verbose,
            )
        )
    resource_plans: List[
        Union[CreateResourcePlan, FailedToPlan]
    ] = await asyncio.gather(*plan_tasks)

    # Update the plans to include dependencies
    resource_name_to_plan: Dict[str, Union[CreateResourcePlan, FailedToPlan]] = {}
    for plan in resource_plans:
        if isinstance(plan, CreateResourcePlan):
            resource_name_to_plan[plan.resource.name] = plan
        elif isinstance(plan, FailedToPlan) and plan.resource is not None:
            resource_name_to_plan[plan.resource.name] = plan

    async def resolve_resource_dependencies_dfs(
        plan: Union[CreateResourcePlan, FailedToPlan],
    ):
        if isinstance(plan, FailedToPlan):
            return plan
        for resource_dependency in plan.resource.inputs_depend_on(environment_state):
            if (
                resource_dependency.name not in resource_name_to_plan
                and resource_dependency.name not in parent_resource_plans
            ):
                resource_manager = environment_manager.create_resource_manager(
                    resource_dependency.name
                )
                try:
                    remote_resource = await resource_manager.load_resource()
                    if remote_resource.product != resource_dependency.product:
                        return FailedToPlan(
                            resource=plan.resource,
                            error_message=f"DependencyProductMismatch: {plan} depends on local resource {ResourceRef(resource_dependency)} which already exists in the environment with a different product.",
                        )
                except exceptions.ResourceNotFound:
                    return FailedToPlan(
                        resource=plan.resource,
                        error_message=f"DependencyNotFound: {plan} depends on local resource {ResourceRef(resource_dependency)} which does not exist in the environment.",
                    )

            else:
                # dependency_plan = resource_name_to_plan[resource_dependency.name]
                dependency_plan = (
                    resource_name_to_plan.get(resource_dependency.name)
                    or parent_resource_plans[resource_dependency.name]
                )

                if isinstance(dependency_plan, FailedToPlan):
                    return FailedToPlan(
                        resource=plan.resource,
                        error_message=f"DependencyFailedToPlan: {plan} depends on {ResourceRef(resource_dependency)} which failed to plan.",
                    )
                if dependency_plan.operation_type == "noop":
                    # TODO: If we ever want to support individual field changes, we will
                    # need to handle it here
                    continue

                resolved_dependency_plan = await resolve_resource_dependencies_dfs(
                    dependency_plan
                )
                if isinstance(resolved_dependency_plan, FailedToPlan):
                    resource_name_to_plan[resource_dependency.name] = (
                        resolved_dependency_plan
                    )
                    return FailedToPlan(
                        resource=plan.resource,
                        error_message=f"DependencyFailedToPlan: {ResourceRef(plan.resource)} depends on {ResourceRef(resource_dependency)} which failed to plan.",
                    )
                plan.depends_on.append(resolved_dependency_plan)

        return plan

    return await asyncio.gather(
        *[
            resolve_resource_dependencies_dfs(plan)
            for plan in resource_name_to_plan.values()
        ]
    )


async def plan_create_service(
    service: Service,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
    parent_resource_plans: Dict[str, CreateResourcePlan],
) -> Union[CreateServicePlan, FailedToPlan]:
    try:
        validate_service_name(service.name)
    except ValueError as e:
        return FailedToPlan(
            service=service,
            error_message=str(e),
        )

    if service.cloud_provider() == CloudProvider.GCP:
        if environment_state.gcp_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use a GCP Service in an AWS Environment.",
            )
    elif service.cloud_provider() == CloudProvider.AWS:
        if environment_state.aws_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use an AWS Service in a GCP Environment.",
            )

    service_manager = environment_manager.create_service_manager(service.name)
    try:
        existing_service = await service_manager.load_service()
    except exceptions.ServiceNotFound:
        existing_service = None

    if existing_service is not None:
        if existing_service.product != service.product:
            exception = exceptions.ServiceProductMismatch(
                service=service,
                existing_product=existing_service.product,
                new_product=service.product,
            )
            return FailedToPlan(
                service=service,
                error_message=str(exception),
            )
        if existing_service.status.is_pending():
            return FailedToPlan(
                service=service,
                error_message=f"ServicePending: Cannot create a service that is already pending. Current status: {existing_service.status}",
            )

    # Plan the resources for the service
    resource_plans = await plan_create_resources(
        *service.resources(),
        environment_state=environment_state,
        environment_manager=environment_manager,
        verbose=verbose,
        parent_resource_plans=parent_resource_plans,
    )
    failed_resource_plans = [
        plan for plan in resource_plans if isinstance(plan, FailedToPlan)
    ]
    if failed_resource_plans:
        return FailedToPlan(
            service=service,
            error_message=f"FailedResourcePlans: {ServiceRef(service)} depends on resources that failed to plan: {failed_resource_plans}",
        )

    return CreateServicePlan(
        resource_or_service=service,
        service_manager=service_manager,
        existing_service_state=existing_service,
        environment_state=environment_state,
        create_resource_plans=resource_plans,  # type: ignore
        depends_on=[],
        verbose=verbose,
    )


async def plan_create_services(
    *services: Service,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
    parent_resource_plans: Dict[str, CreateResourcePlan],
) -> List[Union[CreateResourcePlan, FailedToPlan]]:
    plan_tasks = []
    for service in services:
        plan_tasks.append(
            plan_create_service(
                service=service,
                environment_state=environment_state,
                environment_manager=environment_manager,
                verbose=verbose,
                parent_resource_plans=parent_resource_plans,
            )
        )
    return await asyncio.gather(*plan_tasks)  # type: ignore


async def plan_create(
    *nodes: Node,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
) -> List[Union[CreateResourcePlan, CreateServicePlan, FailedToPlan]]:
    resource_nodes: List[Resource] = []
    service_nodes: List[Service] = []
    for node in nodes:
        if isinstance(node, Resource):
            resource_nodes.append(node)
        elif isinstance(node, Service):
            service_nodes.append(node)
        else:
            raise ValueError(f"Unknown node type {node}")

    resource_plans = await plan_create_resources(
        *resource_nodes,
        environment_state=environment_state,
        environment_manager=environment_manager,
        verbose=verbose,
    )

    keyed_resource_plans = {
        plan.resource.name: plan
        for plan in resource_plans
        if isinstance(plan, CreateResourcePlan)
    }

    service_plans = await plan_create_services(
        *service_nodes,
        environment_state=environment_state,
        environment_manager=environment_manager,
        verbose=verbose,
        parent_resource_plans=keyed_resource_plans,
    )

    return resource_plans + service_plans  # type: ignore


async def create(
    *nodes: Tuple[Node],
    environment: str,
    prompt: bool = True,
    verbose: bool = False,
    console: Console = Console(),
) -> FlowResult:
    """
    Create resources in an environment.

    Args:
    - `nodes`: A tuple of Resources and Services to create.
    - `environment`: The name of the environment to create resources in. Defaults
        to the env configured in the launchflow.yaml.
    - `prompt`: Whether to prompt the user before creating resources.
    - `verbose`: If true all logs will be written to stdout.
    """
    if not nodes:
        console.print("No resources or services to create. Exiting.")
        return FlowResult(success=True, plan_results=[], failed_plans=[])

    if launchflow.project is None:
        console.print("Could not determine the project. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    environment_manager = EnvironmentManager(
        project_name=launchflow.project,
        environment_name=environment,
        backend=config.launchflow_yaml.backend,
    )

    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Planning infrastructure changes...\n", total=None)

        environment_state = await environment_manager.load_environment()
        if environment_state.status == EnvironmentStatus.CREATE_FAILED:
            raise exceptions.EnvironmentInFailedCreateState(environment)

        # Step 1: Build the plans
        create_plans = await plan_create(
            *nodes,  # type: ignore
            environment_state=environment_state,
            environment_manager=environment_manager,
            verbose=verbose,
        )

        progress.remove_task(task)

    failed_plans: List[FailedToPlan] = [
        plan for plan in create_plans if isinstance(plan, FailedToPlan)
    ]

    # Step 2: Select the plan
    print_plans(*create_plans, environment_manager=environment_manager, console=console)

    selected_plans = await select_plans(
        *create_plans,
        operation_type="create",
        environment_manager=environment_manager,
        console=console,
        confirm=prompt,
    )
    if selected_plans is None:  # The None is a special case for no valid plans
        console.print("Nothing to create. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=failed_plans)

    if (
        not selected_plans
    ):  # The empty list case means the user did not confirm any plans
        console.print("No plans selected. Exiting.")
        return FlowResult(success=True, plan_results=[], failed_plans=failed_plans)

    # Step 3: Lock the plans
    # TODO: Determine if we should check if the Environment state has changed since planning
    async with lock_plans(*selected_plans, environment_manager=environment_manager):
        # Step 4: Execute the plans
        console.rule("[bold purple]operations")

        tree = Tree(
            "Plans",
            guide_style=Style(dim=True),
            hide_root=True,
        )
        with Live(Padding(tree, (1, 0, 1, 0)), console=console, refresh_per_second=8):
            all_results = await execute_plans(selected_plans, tree)  # type: ignore

    success = all(result.success for result in all_results)
    flow_result = FlowResult(
        success=success, plan_results=all_results, failed_plans=failed_plans
    )

    resource_results: List[CreateResourceResult] = []
    service_results: List[CreateServiceResult] = []
    for result in all_results:
        if isinstance(result, CreateResourceResult):
            resource_results.append(result)
        elif isinstance(result, CreateServiceResult):
            service_results.append(result)
        else:
            logger.error(
                "Got an unexpected result type %s for plan %s",
                type(result),
                result.plan,
            )

    # Step 5: Print the results

    # TODO: Move this to a shared utility function
    # Step 5.1: Print the logs
    table = Table(
        show_header=True,
        show_edge=False,
        show_lines=False,
        box=None,
        padding=(0, 1),
    )
    table.add_column("Resource", justify="left", overflow="fold")
    table.add_column("Logs", style="blue", overflow="fold")
    if resource_results:
        for result in resource_results:
            if result.logs_file is None:
                continue

            log_link_line = result.logs_file
            if log_link_line.startswith("http"):
                log_link_line = f"[link={log_link_line}]{log_link_line}[/link]"

            if result.success:
                table.add_row(
                    f"[green]✓[/green] {result.plan}",
                    log_link_line,
                )
            else:
                table.add_row(
                    f"[red]✗[/red] {result.plan}",
                    log_link_line,
                )
    if service_results:
        for result in service_results:
            for result in result.create_resource_results:  # type: ignore
                if result.logs_file is None:  # type: ignore
                    continue

                if result.success:
                    table.add_row(
                        f"[green]✓[/green] {result.plan}",
                        result.logs_file,  # type: ignore
                    )
                else:
                    table.add_row(
                        f"[red]✗[/red] {result.plan}",
                        result.logs_file,  # type: ignore
                    )
    if table.row_count > 0:
        console.rule("[bold purple]logs")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # TODO: Move this to a shared utility function
    # Step 5.2: Print the service urls
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Service", justify="left", no_wrap=True)
    table.add_column("URL", style="blue", overflow="fold")
    for result in service_results:
        if result.service_state.service_url:
            table.add_row(
                str(ServiceRef(result.plan.service)), result.service_state.service_url
            )
    if table.row_count > 0:
        console.rule("[bold purple]service urls")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # Step 5.3: Print the dns settings
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Service", justify="left", no_wrap=True)
    table.add_column("Host name", style="light_cyan3", overflow="fold")
    table.add_column("Type", style="yellow3", overflow="fold")
    table.add_column("IP Address", style="pale_green3", overflow="fold")
    for result in service_results:
        if result.dns_outputs is not None:
            for record in result.dns_outputs.dns_records:
                table.add_row(
                    str(ServiceRef(result.plan.service)),
                    result.dns_outputs.domain,
                    record.dns_record_type,
                    record.dns_record_value,
                )

    if table.row_count > 0:
        console.rule("[bold purple]custom domains")
        console.print("Add or update these records in your DNS settings:\n")
        console.print(table, overflow="fold")
        console.print()

    # Step 5.4: Print the secrets
    secrets: List[Resource] = []
    for result in resource_results:
        if is_secret_resource(result.plan.resource) and result.success:
            secrets.append(result.plan.resource)
    if secrets:
        console.rule("[bold purple]secrets")
        console.print("Run these commands to set the value of your secrets:\n")
        for secret in secrets:
            console.print(f"{ResourceRef(secret)}:")
            console.print(
                f"    $ lf secrets set --environment={environment} {secret.name} some-value"
            )
            console.print()

    successful_resource_create_count = 0
    failed_resource_create_count = 0
    successful_resource_update_count = 0
    failed_resource_update_count = 0
    successful_resource_replace_count = 0
    failed_resource_replace_count = 0
    successful_service_create_count = 0
    failed_service_create_count = 0
    successful_service_update_count = 0
    failed_service_update_count = 0

    for result in all_results:
        if isinstance(result, CreateResourceResult):
            if result.success:
                if result.plan.operation_type == "create":
                    successful_resource_create_count += 1
                elif result.plan.operation_type == "update":
                    successful_resource_update_count += 1
                elif result.plan.operation_type == "replace":
                    successful_resource_replace_count += 1
            else:
                if result.plan.operation_type == "create":
                    failed_resource_create_count += 1
                elif result.plan.operation_type == "update":
                    failed_resource_update_count += 1
                elif result.plan.operation_type == "replace":
                    failed_resource_replace_count += 1
        elif isinstance(result, CreateServiceResult):
            if result.success:
                if result.plan.operation_type == "create":
                    successful_service_create_count += 1
                elif result.plan.operation_type == "update":
                    successful_service_update_count += 1
            else:
                if result.plan.operation_type == "create":
                    failed_service_create_count += 1
                elif result.plan.operation_type == "update":
                    failed_service_update_count += 1
            for resource_result in result.create_resource_results:
                if resource_result.success:
                    if resource_result.plan.operation_type == "create":
                        successful_resource_create_count += 1
                    elif resource_result.plan.operation_type == "update":
                        successful_resource_update_count += 1
                    elif resource_result.plan.operation_type == "replace":
                        successful_resource_replace_count += 1
                else:
                    if resource_result.plan.operation_type == "create":
                        failed_resource_create_count += 1
                    elif resource_result.plan.operation_type == "update":
                        failed_resource_update_count += 1
                    elif resource_result.plan.operation_type == "replace":
                        failed_resource_replace_count += 1

    console.rule("[bold purple]summary")
    console.print()

    if successful_resource_create_count or successful_service_create_count:
        if successful_service_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'} and {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
    if failed_resource_create_count or failed_service_create_count:
        if failed_service_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'} and {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
    if successful_resource_update_count or successful_service_update_count:
        if successful_service_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'} and {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
    if failed_resource_update_count or failed_service_update_count:
        if failed_service_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'} and {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
    if successful_resource_replace_count:
        console.print(
            f"[green]Successfully replaced {successful_resource_replace_count} {'resource' if successful_resource_replace_count == 1 else 'resources'}[/green]"
        )
    if failed_resource_replace_count:
        console.print(
            f"[red]Failed to replace {failed_resource_replace_count} {'resource' if failed_resource_replace_count == 1 else 'resources'}[/red]"
        )

    return flow_result
