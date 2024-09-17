import dataclasses
import urllib
from typing import List

import httpx
import rich

import launchflow
from launchflow import exceptions
from launchflow.backend import LaunchFlowBackend
from launchflow.clients.accounts_client import AccountsSyncClient
from launchflow.clients.environments_client import EnvironmentsSyncClient
from launchflow.config import config
from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class LaunchFlowReleaserOutputs(Outputs):
    service_account_email: str


@dataclasses.dataclass
class LaunchFlowReleaserInputs(ResourceInputs):
    launchflow_service_account: str
    permissions: List[str]


class LaunchFlowCloudReleaser(GCPResource[LaunchFlowReleaserOutputs]):
    """A resource for connecting your environment to LaunchFlow Cloud. For additional information see the documentation for the [LaunchFlow Cloud GitHub integration](https://docs.launchflow.com/docs/launchflow-cloud/github-deployments).

    Connecting your environment with `lf cloud connect ${ENV_NAME}` will automatically create this resource.
    """

    product = ResourceProduct.GCP_LAUNCHFLOW_CLOUD_RELEASER.value

    def __init__(self, name: str = "launchflow-releaser") -> None:
        """Create a new LaunchFlowCloudReleaser resource.

        **Args:**
        - `name`: The name of the LaunchFlowCloudReleaser resource. This must be globally unique.
        """
        super().__init__(name=name)
        self.permissions = [
            # Allow triggering cloud build in the project
            "roles/cloudbuild.builds.editor",
            # Allow pushing to the artifact registry and creating new repositories
            "roles/artifactregistry.admin",
            # Allow deploying to cloud run
            "roles/run.admin",
            # Allow writing build logs
            "roles/logging.logWriter",
        ]

    def inputs(self, environment_state: EnvironmentState) -> LaunchFlowReleaserInputs:
        backend = config.launchflow_yaml.backend
        if not isinstance(backend, LaunchFlowBackend):
            raise exceptions.LaunchFlowBackendRequired()
        with httpx.Client() as http_client:
            client = AccountsSyncClient(
                http_client=http_client,
                service_address=backend.lf_cloud_url,
            )
            account = client.connect(config.get_account_id())
        return LaunchFlowReleaserInputs(
            resource_id=self.resource_id,
            launchflow_service_account=account.gcp_service_account_email,
            permissions=self.permissions,
        )

    async def connect_to_launchflow(self):
        """Connect the environment to LaunchFlow Cloud."""
        outputs = await self.outputs_async()
        backend = config.launchflow_yaml.backend
        if not isinstance(backend, LaunchFlowBackend):
            raise exceptions.LaunchFlowBackendRequired()
        with httpx.Client() as http_client:
            client = EnvironmentsSyncClient(
                http_client=http_client,
                launch_service_url=backend.lf_cloud_url,
                launchflow_account_id=config.get_account_id(),
            )
            client.connect_gcp(
                project_name=launchflow.project,
                env_name=launchflow.environment,
                gcp_releaser_service_account=outputs.service_account_email,
                resource_name=self.name,
            )
        rich.print(
            f"[green]Environment `{launchflow.environment}` is now connected to LaunchFlow Cloud![/green]\n"
        )
        rich.print(
            f"Releases will be pushed using the service account we created for you: `{outputs.service_account_email}`. You can learn more at: https://docs.launchflow.com/docs/launchflow-cloud/github-deployments\n"
        )
        # launchflow-services-dev@launchflow-services-dev.iam.gserviceaccount.com
        suffix = outputs.service_account_email.split("@")[1]
        suffix.split(".")[0]
        project = suffix.split(".")[0]

        sa_url_safe = urllib.parse.quote(outputs.service_account_email)
        rich.print(
            "We have granted the service account the minimum required permissions to deploy your app to cloud run. "
            "You may grant any additional permissions as needed via the cloud console:\n\t"
            f"- https://console.cloud.google.com/iam-admin/serviceaccounts/details/{sa_url_safe}?project={project}",
        )
