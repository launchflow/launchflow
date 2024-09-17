import dataclasses
from typing import List

import httpx
import rich

import launchflow
from launchflow import exceptions
from launchflow.aws.resource import AWSResource
from launchflow.backend import LaunchFlowBackend
from launchflow.clients.accounts_client import AccountsSyncClient
from launchflow.clients.environments_client import EnvironmentsSyncClient
from launchflow.config import config
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class LaunchFlowCloudReleaserOutputs(Outputs):
    code_build_project_arn: str
    releaser_role_arn: str


@dataclasses.dataclass
class LaunchFlowCloudReleaserInputs(ResourceInputs):
    launchflow_cloud_aws_account_id: str
    launchflow_cloud_role_name: str
    launchflow_cloud_external_role_id: str
    environment_allowed_actions: List[str] = dataclasses.field(
        default_factory=lambda: [
            "ecs:UpdateService",
            "ecs:DescribeServices",
            "ecs:RegisterTaskDefinition",
            "ecs:DeregisterTaskDefinition",
            "codebuild:StartBuild",
            "codebuild:BatchGetBuilds",
            "ecs:TagResource",
            "ecr:*",
        ]
    )
    account_allowed_actions: List[str] = dataclasses.field(
        default_factory=lambda: [
            "ecs:ListTasks",
            "ecs:DescribeTasks",
            "ecs:DescribeTaskDefinition",
            "ec2:DescribeNetworkInterfaces",
            "ecs:ListClusters",
            "ecs:DescribeClusters",
            "ecs:DescribeContainerInstances",
            "ecs:ListContainerInstances",
            "ecr:GetAuthorizationToken",
        ]
    )


class LaunchFlowCloudReleaser(AWSResource[LaunchFlowCloudReleaserOutputs]):
    """A resource for connecting your environment to LaunchFlow Cloud. For additional information see the documentation for the [LaunchFlow Cloud GitHub integration](https://docs.launchflow.com/docs/launchflow-cloud/github-deployments).

    Connecting your environment with `lf cloud connect ${ENV_NAME}` will automatically create this resource.
    """

    product = ResourceProduct.AWS_LAUNCHFLOW_CLOUD_RELEASER.value

    def __init__(self, name: str = "launchflow-releaser") -> None:
        """Create a new LaunchFlowCloudReleaser resource."""
        super().__init__(
            name=name,
            resource_id=f"{name}-{launchflow.project}-{launchflow.environment}",
        )

    def inputs(
        self, environment_state: EnvironmentState
    ) -> LaunchFlowCloudReleaserInputs:
        backend = config.launchflow_yaml.backend
        if not isinstance(backend, LaunchFlowBackend):
            raise exceptions.LaunchFlowBackendRequired()
        with httpx.Client() as http_client:
            client = AccountsSyncClient(
                http_client=http_client,
                service_address=backend.lf_cloud_url,
            )
            connect = client.connect(config.get_account_id())
        return LaunchFlowCloudReleaserInputs(
            resource_id=self.resource_id,
            launchflow_cloud_role_name=connect.aws_role_name,
            launchflow_cloud_aws_account_id=connect.aws_account_id,
            launchflow_cloud_external_role_id=connect.aws_external_role_id,
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
            client.connect_aws(
                project_name=launchflow.project,
                env_name=launchflow.environment,
                code_build_project_arn=outputs.code_build_project_arn,
                releaser_role_arn=outputs.releaser_role_arn,
                resource_name=self.name,
            )
        rich.print(
            f"[green]Environment `{launchflow.environment}` is now connected to LaunchFlow Cloud![/green]\n"
        )
        rich.print(
            f"Releases will be pushed using the IAM role we created for you: `{outputs.releaser_role_arn}` and they will be run in Code Build Project: `{outputs.code_build_project_arn}`. You can learn more at: https://docs.launchflow.com/docs/launchflow-cloud/github-deployments\n"
        )
        rich.print(
            "We have granted the releaser IAM role the minimum required permissions to deploy your app to ECS Fargate. "
            "You may grant any additional permissions as needed via the cloud console."
        )
