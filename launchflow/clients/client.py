import httpx

from launchflow.clients.accounts_client import AccountsAsyncClient
from launchflow.clients.environments_client import EnvironmentsAsyncClient
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.clients.resources_client import ResourcesAsyncClient
from launchflow.clients.services_client import ServicesAsyncClient


class LaunchFlowAsyncClient:
    def __init__(self, base_url: str, launchflow_account_id: str) -> None:
        self.http_client = httpx.AsyncClient(timeout=60)

        self.accounts = AccountsAsyncClient(self.http_client)
        self.environments = EnvironmentsAsyncClient(
            self.http_client, base_url, launchflow_account_id
        )
        self.projects = ProjectsAsyncClient(
            self.http_client, base_url, launchflow_account_id
        )
        self.resources = ResourcesAsyncClient(
            self.http_client, base_url, launchflow_account_id
        )
        self.services = ServicesAsyncClient(
            self.http_client, base_url, launchflow_account_id
        )

    async def close(self):
        await self.http_client.aclose()
