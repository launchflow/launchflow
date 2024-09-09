import httpx

from launchflow.config import config
from launchflow.exceptions import LaunchFlowRequestFailure, ProjectNotFound
from launchflow.models.flow_state import ProjectState


class ProjectsAsyncClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        launchflow_account_id: str,
    ):
        self.http_client = http_client
        self.url = f"{base_url}/v1/projects"
        self._launchflow_account_id = launchflow_account_id

    @property
    def access_token(self):
        return config.get_access_token()

    async def create(self, project_name: str):
        response = await self.http_client.post(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return ProjectState.model_validate(response.json())

    async def get(self, project_name: str):
        response = await self.http_client.get(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code == 404:
            raise ProjectNotFound(project_name)
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return ProjectState.model_validate(response.json())

    async def list(self):
        response = await self.http_client.get(
            f"{self.url}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return [
            ProjectState.model_validate(project)
            for project in response.json()["projects"]
        ]

    async def delete(self, project_name: str):
        response = await self.http_client.delete(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()


class ProjectsSyncClient:
    def __init__(
        self,
        http_client: httpx.Client,
        launchflow_account_id: str,
    ):
        self.http_client = http_client
        self._launchflow_account_id = launchflow_account_id
        self.url = f"{config.get_launchflow_cloud_url()}/v1/projects"

    @property
    def access_token(self):
        return config.get_access_token()

    def create(self, project_name: str):
        response = self.http_client.post(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return ProjectState.model_validate(response.json())

    def get(self, project_name: str):
        response = self.http_client.get(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return ProjectState.model_validate(response.json())

    def list(self):
        response = self.http_client.get(
            f"{self.url}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return [
            ProjectState.model_validate(project)
            for project in response.json()["projects"]
        ]

    def delete(self, project_name: str):
        response = self.http_client.delete(
            f"{self.url}/{project_name}?account_id={self._launchflow_account_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if response.status_code != 200:
            raise LaunchFlowRequestFailure(response)
        return response.json()
