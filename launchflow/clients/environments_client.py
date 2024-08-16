from typing import Any, Dict

import httpx

from launchflow.config import config
from launchflow.exceptions import LaunchFlowRequestFailure
from launchflow.models.flow_state import EnvironmentState


class EnvironmentsSyncClient:
    def __init__(
        self,
        http_client: httpx.Client,
        launch_service_url: str,
        launchflow_account_id: str,
    ):
        self.http_client = http_client
        self._launch_service_url = launch_service_url
        self._launchflow_account_id = launchflow_account_id

    @property
    def access_token(self):
        return config.get_access_token()

    def base_url(self, project_name: str) -> str:
        return f"{self._launch_service_url}/v1/projects/{project_name}/environments"

    def create(
        self,
        project_name: str,
        env_name: str,
        environment_state: EnvironmentState,
        lock_id: str,
    ) -> EnvironmentState:
        body = {
            "flow_state_environment": environment_state.model_dump(mode="json"),
            "lock_id": lock_id,
        }
        response = self.http_client.post(
            f"{self.base_url(project_name)}/{env_name}?account_id={self._launchflow_account_id}",
            json=body,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return EnvironmentState.model_validate(response.json())

    def get(self, project_name: str, env_name: str) -> EnvironmentState:
        url = f"{self.base_url(project_name)}/{env_name}?account_id={self._launchflow_account_id}"
        response = self.http_client.get(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return EnvironmentState.model_validate(response.json())

    def list(self, project_name: str):
        response = self.http_client.get(
            f"{self.base_url(project_name)}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return {
            name: EnvironmentState.model_validate(env)
            for name, env in response.json()["environments"].items()
        }

    def delete(self, project_name: str, env_name: str, lock_id: str):
        url = f"{self.base_url(project_name)}/{env_name}?lock_id={lock_id}&account_id={self._launchflow_account_id}"
        response = self.http_client.delete(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()

    def connect_gcp(
        self,
        project_name: str,
        env_name: str,
        *,
        gcp_releaser_service_account: str,
        resource_name: str,
    ):
        url = f"{self.base_url(project_name)}/{env_name}/connect?account_id={self._launchflow_account_id}"
        response = self.http_client.patch(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "gcp_connection_info": {
                    "releaser_service_account_email": gcp_releaser_service_account
                },
                "resource_name": resource_name,
            },
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()

    def connect_aws(
        self,
        project_name: str,
        env_name: str,
        *,
        resource_name: str,
        releaser_role_arn: str,
        code_build_project_arn: str,
    ):
        url = f"{self.base_url(project_name)}/{env_name}/connect?account_id={self._launchflow_account_id}"
        response = self.http_client.patch(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "aws_connection_info": {
                    "releaser_role_arn": releaser_role_arn,
                    "code_build_project_arn": code_build_project_arn,
                },
                "resource_name": resource_name,
            },
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()


class EnvironmentsAsyncClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        launch_service_url: str,
        launchflow_account_id: str,
    ):
        self.http_client = http_client
        self._launch_service_url = launch_service_url
        self._launchflow_account_id = launchflow_account_id

    @property
    def access_token(self):
        return config.get_access_token()

    def base_url(self, project_name: str) -> str:
        return f"{self._launch_service_url}/v1/projects/{project_name}/environments"

    async def create(
        self,
        project_name: str,
        env_name: str,
        environment_state: EnvironmentState,
        lock_id: str,
    ) -> EnvironmentState:
        response = await self.http_client.post(
            f"{self.base_url(project_name)}/{env_name}?lock_id={lock_id}&account_id={self._launchflow_account_id}",
            json=environment_state.to_dict(),
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return EnvironmentState.model_validate(response.json())

    async def get(self, project_name: str, env_name: str) -> EnvironmentState:
        url = f"{self.base_url(project_name)}/{env_name}?account_id={self._launchflow_account_id}"
        response = await self.http_client.get(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return EnvironmentState.model_validate(response.json())

    async def list(self, project_name):
        response = await self.http_client.get(
            f"{self.base_url(project_name)}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return {
            name: EnvironmentState.model_validate(env)
            for name, env in response.json()["environments"].items()
        }

    async def delete(self, project_name: str, env_name: str, lock_id: str):
        url = f"{self.base_url(project_name)}/{env_name}?lock_id={lock_id}&account_id={self._launchflow_account_id}"
        response = await self.http_client.delete(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()

    async def write_tofu_state(
        self, project_name: str, env_name: str, tofu_state: Dict[str, Any], lock_id: str
    ):
        url = f"{self.base_url(project_name)}/{env_name}/tofu-state?lock_id={lock_id}&account_id={self._launchflow_account_id}"
        response = await self.http_client.post(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=tofu_state,
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
