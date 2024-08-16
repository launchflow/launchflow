import asyncio
import os
from typing import Dict, Union

import httpx
import yaml

from launchflow import exceptions
from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.clients.environments_client import EnvironmentsAsyncClient
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.config import config
from launchflow.gcp_clients import get_storage_client, read_from_gcs, write_to_gcs
from launchflow.managers.base import BaseManager
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models.flow_state import EnvironmentState, ProjectState


def _save_local_project_state(project_state: ProjectState, path: str):
    base_path = os.path.join(os.path.abspath(path), project_state.name)
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    flow_path = os.path.join(base_path, "flow.state")
    with open(flow_path, "w") as f:
        json_data = project_state.to_dict()
        yaml.dump(json_data, f, sort_keys=False)


async def _save_gcs_project_state(
    project_state: ProjectState, bucket: str, prefix: str
):
    base_path = os.path.join(prefix, project_state.name, "flow.state")
    await write_to_gcs(
        bucket,
        base_path,
        yaml.dump(project_state.to_dict(), sort_keys=False),
    )


async def _load_project_state_from_gcs(project_name: str, backend: GCSBackend):
    flow_path = os.path.join(backend.prefix, project_name, "flow.state")
    try:
        raw_state = yaml.safe_load(await read_from_gcs(backend.bucket, flow_path))
        state = ProjectState.model_validate(raw_state)
        return state
    except exceptions.GCSObjectNotFound:
        raise exceptions.ProjectStateNotFound()


async def _load_project_state_from_launchflow(
    project_name: str,
    launch_flow_url: str,
    launchflow_account_id: str,
):
    async with httpx.AsyncClient(timeout=60) as client:
        projects_client = ProjectsAsyncClient(
            client, launch_flow_url, launchflow_account_id
        )
        try:
            state = await projects_client.get(project_name)
        except exceptions.LaunchFlowRequestFailure as e:
            if e.status_code == 404:
                raise exceptions.LaunchFlowProjectNotFound(project_name)
            raise e

        return state


def _load_project_state_from_local(project_name: str, backend: LocalBackend):
    flow_path = os.path.join(os.path.abspath(backend.path), project_name, "flow.state")
    try:
        with open(flow_path, "r") as f:
            raw_project_state = yaml.safe_load(f)
            project_state = ProjectState.model_validate(raw_project_state)
    except FileNotFoundError:
        raise exceptions.ProjectStateNotFound()
    return project_state


class ProjectManager(BaseManager):
    def __init__(
        self,
        project_name: str,
        backend: Union[LocalBackend, LaunchFlowBackend, GCSBackend],
    ) -> None:
        super().__init__(
            backend=backend,
        )
        self.project_name: str = project_name

    async def load_project_state(self) -> ProjectState:
        if isinstance(self.backend, LocalBackend):
            return _load_project_state_from_local(self.project_name, self.backend)
        elif isinstance(self.backend, LaunchFlowBackend):
            return await _load_project_state_from_launchflow(
                self.project_name,
                self.backend.lf_cloud_url,
                config.get_account_id(),
            )
        elif isinstance(self.backend, GCSBackend):
            return await _load_project_state_from_gcs(self.project_name, self.backend)

    async def save_project_state(self, project_state: ProjectState) -> None:
        if isinstance(self.backend, LocalBackend):
            _save_local_project_state(project_state, self.backend.path)
        elif isinstance(self.backend, GCSBackend):
            await _save_gcs_project_state(
                project_state, self.backend.bucket, self.backend.prefix
            )
        elif isinstance(self.backend, LaunchFlowBackend):
            # NOTE: inpractice this will never be called because this is only used for tests
            raise ValueError(
                "LaunchFlow flow state should be saved using `lf projects create`"
            )
        else:
            raise NotImplementedError("Only local backend is supported")

    async def list_environments(self) -> Dict[str, EnvironmentState]:
        if isinstance(self.backend, LocalBackend):
            # Load the environments
            envs = {}
            if os.path.exists(os.path.join(self.backend.path, self.project_name)):
                for dir in os.scandir(
                    os.path.join(self.backend.path, self.project_name)
                ):
                    if dir.is_dir():
                        if os.path.exists(os.path.join(dir.path, "flow.state")):
                            env_name = os.path.basename(dir.path)
                            env_path = os.path.join(dir.path, "flow.state")
                            with open(env_path, "r") as f:
                                raw_env = yaml.safe_load(f)
                                env = EnvironmentState.model_validate(raw_env)
                                envs[env_name] = env
            return envs
        elif isinstance(self.backend, LaunchFlowBackend):
            async with httpx.AsyncClient(timeout=60) as client:
                env_client = EnvironmentsAsyncClient(
                    client,
                    self.backend.lf_cloud_url,
                    config.get_account_id(),
                )
                try:
                    return await env_client.list(self.project_name)
                except exceptions.LaunchFlowRequestFailure as e:
                    if e.status_code == 404:
                        raise exceptions.LaunchFlowProjectNotFound(self.project_name)
                    raise e
        elif isinstance(self.backend, GCSBackend):
            envs = {}

            def read_blobs():
                gcs_client = get_storage_client()
                bucket = gcs_client.bucket(self.backend.bucket)
                blobs = bucket.list_blobs(
                    prefix=os.path.join(self.backend.prefix, self.project_name)
                )
                for blob in blobs:
                    relative_path = blob.name.replace(
                        os.path.join(self.backend.prefix, self.project_name) + "/", ""
                    )
                    split_path = relative_path.split("/")
                    if relative_path.endswith("flow.state") and len(split_path) == 2:
                        env_name = blob.name.split("/")[-2]
                        raw_env = yaml.safe_load(
                            blob.download_as_bytes().decode("utf-8")
                        )
                        env = EnvironmentState.model_validate(raw_env)
                        envs[env_name] = env
                return envs

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, read_blobs)

    def create_environment_manager(self, environment_name: str) -> EnvironmentManager:
        return EnvironmentManager(
            project_name=self.project_name,
            environment_name=environment_name,
            backend=self.backend,
        )
