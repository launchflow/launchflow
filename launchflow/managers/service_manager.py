import asyncio
import os
import shutil
from typing import Union

import httpx
import yaml

from launchflow import exceptions
from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.clients.services_client import ServicesAsyncClient
from launchflow.config import config
from launchflow.gcp_clients import get_storage_client, read_from_gcs, write_to_gcs
from launchflow.locks import GCSLock, LaunchFlowLock, LocalLock, Lock, LockOperation
from launchflow.managers.base import BaseManager
from launchflow.models.flow_state import ServiceState

# TODO: need to add tests to this file once it is all working


def _load_local_service(path: str, name: str, project_name: str, env_name: str):
    base_service_path = os.path.join(path, project_name, env_name, "services", name)
    service_path = os.path.join(base_service_path, "flow.state")
    try:
        with open(service_path, "r") as f:
            raw_service = yaml.safe_load(f)
            service = ServiceState.model_validate(raw_service)
        return service
    except FileNotFoundError:
        raise exceptions.ServiceNotFound(name)


async def _load_gcs_service(
    bucket: str,
    prefix: str,
    project_name: str,
    environment_name: str,
    service_name: str,
):
    # TODO: throw a not found error if we can't find the environment
    env_path = os.path.join(
        prefix, project_name, environment_name, "services", service_name, "flow.state"
    )
    try:
        raw_state = yaml.safe_load(await read_from_gcs(bucket, env_path))
        state = ServiceState.model_validate(raw_state)
    except exceptions.GCSObjectNotFound:
        raise exceptions.ServiceNotFound(service_name)
    return state


async def _load_launchflow_service(
    project_name: str,
    environment_name: str,
    service_name: str,
    launch_url: str,
    launchflow_account_id: str,
) -> ServiceState:
    async with httpx.AsyncClient(timeout=60) as client:
        services_client = ServicesAsyncClient(
            client,
            base_url=launch_url,
            launchflow_account_id=launchflow_account_id,
        )
        try:
            state = await services_client.get(
                project_name, environment_name, service_name=service_name
            )
        except exceptions.LaunchFlowRequestFailure as e:
            if e.status_code == 404:
                raise exceptions.ServiceNotFound(service_name)
            raise e

        return state


def _save_local_service(
    service: ServiceState,
    path: str,
    project_name,
    environment_name: str,
    service_name: str,
):
    service_path = os.path.join(
        path, project_name, environment_name, "services", service_name
    )
    service_file = os.path.join(service_path, "flow.state")
    if not os.path.exists(service_path):
        os.makedirs(service_path)
    with open(service_file, "w") as f:
        json_data = service.to_dict()
        yaml.dump(json_data, f, sort_keys=False)


async def _save_gcs_service(
    service: ServiceState,
    bucket: str,
    prefix: str,
    project_name: str,
    environment_name: str,
    service_name: str,
):
    service_path = os.path.join(
        prefix, project_name, environment_name, "services", service_name, "flow.state"
    )
    await write_to_gcs(
        bucket,
        service_path,
        yaml.dump(service.to_dict(), sort_keys=False),
    )


async def _save_launchflow_service(
    service: ServiceState,
    project_name: str,
    environment_name: str,
    service_name: str,
    lock_id: str,
    launch_url: str,
    launchflow_account_id: str,
):
    async with httpx.AsyncClient(timeout=60) as client:
        services_client = ServicesAsyncClient(client, launch_url, launchflow_account_id)
        await services_client.save(
            project_name=project_name,
            environment_name=environment_name,
            service_name=service_name,
            flow_state=service,
            lock_id=lock_id,
        )


def _delete_local_service(
    path: str, project_name: str, environment_name: str, service_name: str
):
    service_path = os.path.join(
        path, project_name, environment_name, "services", service_name
    )
    shutil.rmtree(service_path)


class ServiceManager(BaseManager):
    def __init__(
        self,
        project_name: str,
        environment_name: str,
        service_name: str,
        backend: Union[LocalBackend, LaunchFlowBackend, GCSBackend],
    ) -> None:
        super().__init__(backend)
        self.project_name = project_name
        self.environment_name = environment_name
        self.service_name = service_name

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, ServiceManager):
            return (
                self.project_name == __value.project_name
                and self.environment_name == __value.environment_name
                and self.service_name == __value.service_name
            )
        return False

    async def load_service(self) -> ServiceState:
        if isinstance(self.backend, LocalBackend):
            return _load_local_service(
                self.backend.path,
                self.service_name,
                self.project_name,
                self.environment_name,
            )
        elif isinstance(self.backend, LaunchFlowBackend):
            return await _load_launchflow_service(
                self.project_name,
                self.environment_name,
                self.service_name,
                self.backend.lf_cloud_url,
                config.get_account_id(),
            )
        elif isinstance(self.backend, GCSBackend):
            return await _load_gcs_service(
                self.backend.bucket,
                self.backend.prefix,
                self.project_name,
                self.environment_name,
                self.service_name,
            )

    async def save_service(self, service: ServiceState, lock_id: str):
        if isinstance(self.backend, LocalBackend):
            _save_local_service(
                service,
                self.backend.path,
                self.project_name,
                self.environment_name,
                self.service_name,
            )
        elif isinstance(self.backend, LaunchFlowBackend):
            await _save_launchflow_service(
                service,
                self.project_name,
                self.environment_name,
                self.service_name,
                lock_id,
                self.backend.lf_cloud_url,
                config.get_account_id(),
            )
        elif isinstance(self.backend, GCSBackend):
            await _save_gcs_service(
                service,
                self.backend.bucket,
                self.backend.prefix,
                self.project_name,
                self.environment_name,
                self.service_name,
            )

    async def delete_service(self, lock_id: str):
        if isinstance(self.backend, LocalBackend):
            _delete_local_service(
                self.backend.path,
                self.project_name,
                self.environment_name,
                self.service_name,
            )
        elif isinstance(self.backend, GCSBackend):

            def delete_blobs():
                client = get_storage_client()
                blobs = client.list_blobs(
                    bucket_or_name=self.backend.bucket,
                    prefix=os.path.join(
                        self.backend.prefix,
                        self.project_name,
                        self.environment_name,
                        "services",
                        self.service_name,
                    )
                    # NOTE: the trailing slash is important here
                    # otherwise we would delete other services with a similar prefix
                    + "/",
                )
                for blob in blobs:
                    blob.delete()

            # TODO: Make sure this works in jupyter notebooks
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, delete_blobs)
        elif isinstance(self.backend, LaunchFlowBackend):
            async with httpx.AsyncClient(timeout=60) as client:
                services_client = ServicesAsyncClient(
                    client,
                    base_url=self.backend.lf_cloud_url,
                    launchflow_account_id=config.get_account_id(),
                )
                await services_client.delete(
                    project_name=self.project_name,
                    environment_name=self.environment_name,
                    service_name=self.service_name,
                    lock_id=lock_id,
                )
        else:
            raise NotImplementedError(f"{self.backend} is not supported yet.")

    async def lock_service(self, operation: LockOperation) -> Lock:
        if isinstance(self.backend, LocalBackend):
            env_path = os.path.join(
                self.backend.path,
                self.project_name,
                self.environment_name,
                "services",
                self.service_name,
            )
            lock = LocalLock(env_path, operation)
        elif isinstance(self.backend, GCSBackend):
            lock = GCSLock(  # type: ignore
                self.backend.bucket,
                self.backend.prefix,
                self.project_name,
                f"{self.environment_name}/services/{self.service_name}",
                operation,
            )
        elif isinstance(self.backend, LaunchFlowBackend):
            lock = LaunchFlowLock(  # type: ignore
                project=self.project_name,
                entity_path=f"environments/{self.environment_name}/services/{self.service_name}",
                operation=operation,
                launch_url=self.backend.lf_cloud_url,
                launchflow_account_id=config.get_account_id(),
            )
        else:
            raise NotImplementedError(f"{self.backend} is not supported yet.")
        await lock.acquire()
        return lock

    async def force_unlock_service(self):
        if isinstance(self.backend, LocalBackend):
            env_path = os.path.join(
                self.backend.path,
                self.project_name,
                self.environment_name,
                "services",
                self.service_name,
            )
            await LocalLock.force_unlock(env_path)
        elif isinstance(self.backend, GCSBackend):
            await GCSLock.force_unlock(
                self.backend.bucket,
                self.backend.prefix,
                self.project_name,
                f"{self.environment_name}/services/{self.service_name}",
            )
        elif isinstance(self.backend, LaunchFlowBackend):
            await LaunchFlowLock.force_unlock(
                project=self.project_name,
                entity_path=f"environments/{self.environment_name}/services/{self.service_name}",
                launch_url=self.backend.lf_cloud_url,
                launchflow_account_id=config.get_account_id(),
            )
        else:
            raise NotImplementedError(f"{self.backend} is not supported yet.")
