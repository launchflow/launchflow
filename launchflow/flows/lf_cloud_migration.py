import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import rich

import launchflow
from launchflow import exceptions
from launchflow.backend import Backend, GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.clients.environments_client import EnvironmentsAsyncClient
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.clients.resources_client import ResourcesAsyncClient
from launchflow.config import config
from launchflow.exceptions import ProjectNotFound, ProjectStateNotFound
from launchflow.flows.project_flows import create_project
from launchflow.gcp_clients import write_to_gcs
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.flow_state import ProjectState, ResourceState
from launchflow.models.launchflow_uri import LaunchFlowURI


async def write_tofu_state_to_gcs(
    bucket: str, state_prefix: str, tofu_state: Dict[str, Any]
) -> None:
    """Write Terraform state to GCS bucket at the specified state prefix.

    Args:
        bucket: GCS bucket name
        state_prefix: Path prefix for the state file in the bucket
        tofu_state: Terraform state data to write
    """
    state_data = json.dumps(tofu_state, indent=2)
    state_path = f"{state_prefix}/default.tfstate"
    if state_path.startswith("/"):
        state_path = state_path[1:]
    await write_to_gcs(bucket, state_path, state_data)


async def _migrate_resource(
    source_rm: ResourceManager,
    target_rm: ResourceManager,
    httpx_client: httpx.AsyncClient,
):
    source_resource = await source_rm.load_resource()
    try:
        _ = await target_rm.load_resource()
        rich.print(
            f"[red]Resource {source_rm.resource_name} already exists in the target environment.[/red]"
        )
    except exceptions.ResourceNotFound:
        async with await target_rm.lock_resource(
            operation=LockOperation(OperationType.MIGRATE_RESOURCE)
        ) as lock:
            resource_client = ResourcesAsyncClient(
                http_client=httpx_client,
                base_url=source_rm.backend.lf_cloud_url
                if isinstance(source_rm.backend, LaunchFlowBackend)
                else target_rm.backend.lf_cloud_url,  # type: ignore
                launchflow_account_id=config.get_account_id(),
            )
            await target_rm.save_resource(source_resource, lock.lock_id)
            tofu_states = await _get_resource_tofu_states(
                source_rm, resource_client, source_resource
            )
            tofu_state_coros = []
            for module, tofu_state in tofu_states.items():
                if isinstance(target_rm.backend, LaunchFlowBackend):
                    tofu_state_coros.append(
                        resource_client.write_tofu_state(
                            project_name=target_rm.project_name,
                            environment_name=target_rm.environment_name,
                            resource_name=target_rm.resource_name,
                            module_name=module,
                            tofu_state=tofu_state,
                            lock_id=lock.lock_id,
                        )
                    )
                elif isinstance(target_rm.backend, GCSBackend):
                    uri = LaunchFlowURI(
                        project_name=target_rm.project_name,
                        environment_name=target_rm.environment_name,
                        resource_name=target_rm.resource_name,
                    )
                    state_prefix = uri.tf_state_prefix(module, target_rm.backend)
                    bucket = target_rm.backend.bucket
                    tofu_state_coros.append(
                        write_tofu_state_to_gcs(bucket, state_prefix, tofu_state)
                    )
                else:
                    raise ValueError(
                        f"Unsupported backend type: {type(target_rm.backend)}"
                    )
            await asyncio.gather(*tofu_state_coros)
        rich.print(
            f"[green]Resource {source_rm.resource_name} migrated successfully.[/green]"
        )


async def _migrate_service(
    source_sm: ServiceManager,
    target_sm: ServiceManager,
    httpx_client: httpx.AsyncClient,
):
    source_service = await source_sm.load_service()
    try:
        _ = await target_sm.load_service()
        rich.print(
            f"[red]Service {source_sm.service_name} already exists in the target environment.[/red]"
        )
    except exceptions.ServiceNotFound:
        async with await target_sm.lock_service(
            operation=LockOperation(OperationType.MIGRATE_SERVICE)
        ) as lock:
            await target_sm.save_service(source_service, lock.lock_id)
            # TODO: I think we got rid of these so no need to move tofu states any more
            # tofu_states = await _get_service_tofu_states(source_sm)
            # tofu_state_coros = []
            # services_client = ServicesAsyncClient(
            #     http_client=httpx_client,
            #     base_url=target_sm.backend.lf_cloud_url,  # type: ignore
            #     launchflow_account_id=config.get_account_id(),
            # )
            # for module, tofu_state in tofu_states.items():
            #     tofu_state_coros.append(
            #         services_client.write_tofu_state(
            #             project_name=target_sm.project_name,
            #             environment_name=target_sm.environment_name,
            #             service_name=target_sm.service_name,
            #             module_name=module,
            #             tofu_state=tofu_state,
            #             lock_id=lock.lock_id,
            #         )
            #     )
            # await asyncio.gather(*tofu_state_coros)
        rich.print(
            f"[green]Service {source_sm.service_name} migrated successfully.[/green]"
        )


async def _get_environment_tofu_state(
    em: EnvironmentManager,
    environment_client: EnvironmentsAsyncClient,
) -> Optional[Dict[str, Any]]:
    if isinstance(em.backend, LocalBackend):
        tofu_path = os.path.join(
            em.backend.path, em.project_name, em.environment_name, "default.tfstate"
        )
        if os.path.exists(tofu_path):
            with open(tofu_path, "r") as f:
                return json.load(f)
        return None
    elif isinstance(em.backend, LaunchFlowBackend):
        return await environment_client.read_tofu_state(
            em.project_name, em.environment_name
        )
    else:
        raise NotImplementedError(
            f"Getting tofu state from {em.backend.__class__.__name__} is not supported."
        )


async def _get_service_tofu_states(sm: ServiceManager) -> Dict[str, Dict[str, Any]]:
    if isinstance(sm.backend, LocalBackend):
        base_path = os.path.join(
            sm.backend.path,
            sm.project_name,
            sm.environment_name,
            "services",
            sm.service_name,
        )
        tofu_states = {}
        for root, _, files in os.walk(base_path):
            for f in files:
                if f == "default.tfstate":
                    module = os.path.basename(root)
                    tofu_path = os.path.join(root, f)
                    with open(tofu_path, "r") as f:  # type: ignore
                        tofu_states[module] = json.load(f)  # type: ignore
        return tofu_states
    else:
        raise NotImplementedError(
            f"Getting tofu state from {sm.backend.__class__.__name__} is not supported."
        )


async def _get_resource_tofu_states(
    rm: ResourceManager, client: ResourcesAsyncClient, source: ResourceState
) -> Dict[str, Dict[str, Any]]:
    if isinstance(rm.backend, LocalBackend):
        base_path = os.path.join(
            rm.backend.path,
            rm.project_name,
            rm.environment_name,
            "resources",
            rm.resource_name,
        )
        tofu_states = {}
        for root, _, files in os.walk(base_path):
            for f in files:
                if f == "default.tfstate":
                    module = os.path.basename(root)
                    tofu_path = os.path.join(root, f)
                    with open(tofu_path, "r") as f:  # type: ignore
                        tofu_states[module] = json.load(f)  # type: ignore
        return tofu_states
    elif isinstance(rm.backend, LaunchFlowBackend):
        try:
            tofu_state = await client.read_tofu_state(
                rm.project_name, rm.environment_name, rm.resource_name, source.product
            )
        except exceptions.LaunchFlowRequestFailure as e:
            if e.status_code == 404:
                logging.warning(
                    f"Unable to retrieve tofu state for resource: {rm.resource_name}"
                )
                return {}
            tofu_state = {}
        return {source.product: tofu_state}
    else:
        raise NotImplementedError(
            f"Getting tofu state from {rm.backend.__class__.__name__} is not supported."
        )


async def _migrate_environment(
    source_em: EnvironmentManager,
    target_em: EnvironmentManager,
    httpx_client: httpx.AsyncClient,
):
    source_env = await source_em.load_environment()
    try:
        _ = await target_em.load_environment()
        rich.print(
            f"[red]Environment {source_em.environment_name} already exists in the target project.[/red]"
        )
    except exceptions.EnvironmentNotFound:
        environment_client = EnvironmentsAsyncClient(
            http_client=httpx_client,
            launch_service_url=source_em.backend.lf_cloud_url
            if isinstance(source_em.backend, LaunchFlowBackend)
            else target_em.backend.lf_cloud_url,  # type: ignore
            launchflow_account_id=config.get_account_id(),
        )
        async with await target_em.lock_environment(
            operation=LockOperation(OperationType.MIGRATE_ENVIRONMENT)
        ) as lock:
            await target_em.save_environment(source_env, lock_id=lock.lock_id)
            tofu_state = await _get_environment_tofu_state(
                source_em, environment_client
            )
            if tofu_state is not None:
                if isinstance(target_em.backend, LaunchFlowBackend):
                    await environment_client.write_tofu_state(
                        project_name=target_em.project_name,
                        env_name=target_em.environment_name,
                        tofu_state=tofu_state,
                        lock_id=lock.lock_id,
                    )
                elif isinstance(target_em.backend, GCSBackend):
                    uri = LaunchFlowURI(
                        project_name=target_em.project_name,
                        environment_name=target_em.environment_name,
                    )
                    state_prefix = uri.tf_state_prefix(backend=target_em.backend)
                    bucket = target_em.backend.bucket
                    await write_tofu_state_to_gcs(bucket, state_prefix, tofu_state)
                else:
                    raise ValueError(
                        f"Unsupported backend type: {type(target_em.backend)}"
                    )

    source_resources = await source_em.list_resources()
    for name, resource in source_resources.items():
        source_rm = source_em.create_resource_manager(name)
        target_rm = target_em.create_resource_manager(name)
        await _migrate_resource(source_rm, target_rm, httpx_client)

    source_servicse = await source_em.list_services()
    for name, env in source_servicse.items():
        source_sm = source_em.create_service_manager(name)
        target_sm = target_em.create_service_manager(name)
        await _migrate_service(source_sm, target_sm, httpx_client)

    rich.print(
        f"[green]Environment {source_em.environment_name} migrated successfully.[/green]"
    )


async def migrate(source: Backend, target: Backend):
    if not isinstance(source, (LocalBackend, GCSBackend, LaunchFlowBackend)):
        raise NotImplementedError(
            "Only local and GCS backends are supported as source."
        )
    if not isinstance(target, (GCSBackend, LaunchFlowBackend)):
        raise NotImplementedError(
            "Only LaunchFlow Cloud and GCS backends are supported as target."
        )
    async with httpx.AsyncClient(timeout=60) as client:
        project = launchflow.project
        account_id = config.get_account_id()
        # 1. migrate the project
        source_project_manager = ProjectManager(backend=source, project_name=project)
        target_project_manager = ProjectManager(backend=target, project_name=project)

        try:
            # TODO: maybe we should move this logic into save project state
            _ = await target_project_manager.load_project_state()
        except (ProjectNotFound, ProjectStateNotFound):
            if isinstance(target, LaunchFlowBackend):
                proj_client = ProjectsAsyncClient(
                    client,
                    base_url=target.lf_cloud_url,
                    launchflow_account_id=config.get_account_id(),
                )
                await create_project(
                    client=proj_client,
                    account_id=account_id,
                    project_name=project,
                    prompt=True,
                )
            else:
                await target_project_manager.save_project_state(
                    ProjectState(
                        name=project,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                )

        # 2. Migrate the environments
        source_envs = await source_project_manager.list_environments()
        for name, env in source_envs.items():
            source_em = source_project_manager.create_environment_manager(name)
            target_em = target_project_manager.create_environment_manager(name)
            await _migrate_environment(source_em, target_em, client)
