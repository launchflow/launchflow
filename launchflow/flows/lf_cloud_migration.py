import asyncio
import json
import os
from typing import Any, Dict, Optional

import httpx
import rich

import launchflow
from launchflow import exceptions
from launchflow.backend import Backend, GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.clients.environments_client import EnvironmentsAsyncClient
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.clients.resources_client import ResourcesAsyncClient
from launchflow.clients.services_client import ServicesAsyncClient
from launchflow.config import config
from launchflow.exceptions import ProjectNotFound
from launchflow.flows.project_flows import create_project
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager


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
            await target_rm.save_resource(source_resource, lock.lock_id)
            tofu_states = await _get_resource_tofu_states(source_rm)
            tofu_state_coros = []
            resource_client = ResourcesAsyncClient(
                http_client=httpx_client,
                base_url=target_rm.backend.lf_cloud_url,  # type: ignore
                launchflow_account_id=config.get_account_id(),
            )
            for module, tofu_state in tofu_states.items():
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
            tofu_states = await _get_service_tofu_states(source_sm)
            tofu_state_coros = []
            services_client = ServicesAsyncClient(
                http_client=httpx_client,
                base_url=target_sm.backend.lf_cloud_url,  # type: ignore
                launchflow_account_id=config.get_account_id(),
            )
            for module, tofu_state in tofu_states.items():
                tofu_state_coros.append(
                    services_client.write_tofu_state(
                        project_name=target_sm.project_name,
                        environment_name=target_sm.environment_name,
                        service_name=target_sm.service_name,
                        module_name=module,
                        tofu_state=tofu_state,
                        lock_id=lock.lock_id,
                    )
                )
            await asyncio.gather(*tofu_state_coros)
        rich.print(
            f"[green]Service {source_sm.service_name} migrated successfully.[/green]"
        )


async def _get_environment_tofu_state(
    em: EnvironmentManager,
) -> Optional[Dict[str, Any]]:
    if isinstance(em.backend, LocalBackend):
        tofu_path = os.path.join(
            em.backend.path, em.project_name, em.environment_name, "default.tfstate"
        )
        if os.path.exists(tofu_path):
            with open(tofu_path, "r") as f:
                return json.load(f)
        return None
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


async def _get_resource_tofu_states(rm: ResourceManager) -> Dict[str, Dict[str, Any]]:
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
        # TODO: need to also migrate the tofu state
        environment_client = EnvironmentsAsyncClient(
            http_client=httpx_client,
            launch_service_url=target_em.backend.lf_cloud_url,  # type: ignore
            launchflow_account_id=config.get_account_id(),
        )
        async with await target_em.lock_environment(
            operation=LockOperation(OperationType.MIGRATE_ENVIRONMENT)
        ) as lock:
            await target_em.save_environment(source_env, lock_id=lock.lock_id)
            tofu_state = await _get_environment_tofu_state(source_em)
            if tofu_state is not None:
                await environment_client.write_tofu_state(
                    project_name=target_em.project_name,
                    env_name=target_em.environment_name,
                    tofu_state=tofu_state,
                    lock_id=lock.lock_id,
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


async def migrate(source: Backend, target: LaunchFlowBackend):
    if not isinstance(source, LocalBackend) and not isinstance(source, GCSBackend):
        raise NotImplementedError(
            "Only local and GCS backends are supported as source."
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
        except ProjectNotFound:
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

        # 2. Migrate the environments
        source_envs = await source_project_manager.list_environments()
        for name, env in source_envs.items():
            source_em = source_project_manager.create_environment_manager(name)
            target_em = target_project_manager.create_environment_manager(name)
            await _migrate_environment(source_em, target_em, client)
