from dataclasses import dataclass
from typing import IO, List, Optional

import pkg_resources

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.alb import ApplicationLoadBalancer
from launchflow.aws.codebuild_project import (
    Cache,
    CloudWatchLogsConfig,
    CodeBuildProject,
    Environment,
    EnvironmentVariable,
    LogsConfig,
    Source,
)
from launchflow.aws.ecr_repository import ECRRepository
from launchflow.aws.ecs_cluster import ECSCluster
from launchflow.aws.ecs_fargate_container import ECSFargateServiceContainer
from launchflow.aws.service import AWSService
from launchflow.models.enums import ServiceProduct
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs
from launchflow.workflows.deploy_aws_service import (
    build_ecr_docker_image_locally,
    build_ecr_docker_image_on_code_build,
)


@dataclass
class ECSFargateServiceInputs(Inputs):
    cpu: int = 256
    memory: int = 512
    port: int = 80


@dataclass
class ECSFargateServiceReleaseInputs:
    docker_image: str


class ECSFargateService(AWSService[ECSFargateServiceReleaseInputs]):
    """A service hosted on AWS ECS Fargate.

    Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html).


    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to an ECS Fargate Service in your AWS account
    service = lf.aws.ECSFargateService("my-service")
    ```

    **NOTE:** This will create the following infrastructure in your AWS account:
    - A [ECS Fargate](https://aws.amazon.com/fargate/) service with the specified configuration.
    - An [Application Load Balancer](https://aws.amazon.com/elasticloadbalancing) to route traffic to the service.
    - A [Code Build](https://aws.amazon.com/codebuild) project that builds and deploys Docker images for the service.
    - An [Elastic Container Registry](https://aws.amazon.com/ecr) repository to store the service's Docker image.
    """

    product = ServiceProduct.AWS_ECS_FARGATE.value

    # TODO: Add better support for custom domains + write up a guide for different domain providers
    def __init__(
        self,
        name: str,
        cpu: int = 256,
        memory: int = 512,
        port: int = 80,
        desired_count: int = 1,
        build_directory: str = ".",
        build_ignore: List[str] = [],
        dockerfile: str = "Dockerfile",
        domain: Optional[str] = None,
        cluster: Optional[ECSCluster] = None,
    ) -> None:
        """Creates a new ECS Fargate service.

        **Args:**
        - `name (str)`: The name of the service.
        - `cpu (int)`: The CPU units to allocate to the container. Defaults to 256.
        - `memory (int)`: The memory to allocate to the container. Defaults to 512.
        - `port (int)`: The port the container listens on. Defaults to 80.
        - `desired_count (int)`: The number of tasks to run. Defaults to 1.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `domain (Optional[str])`: The domain name to use for the service. This will create an ACM certificate and configure the ALB to use HTTPS.
        - `certificate (Optional[ACMCertificate])`: An existing ACM certificate to use for the service. This will configure the ALB to use HTTPS.
        - `cluster (Optional[ECSCluster])`: The ECS cluster to use for the service. If not provided, a new cluster will be created.
        """
        if domain is not None:
            raise exceptions.ComingSoon(issue_number=83)

        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args={
                "dockerfile": dockerfile,
            },
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"
        # Resources - flows should not access these directly
        self._ecr = ECRRepository(
            f"{name}-ecr", force_delete=True, image_tag_mutability="MUTABLE"
        )
        self._ecr.resource_id = resource_id_with_launchflow_prefix.lower()

        # Builds an absolute path to the buildspec.yml file packaged with launchflow
        buildspec_path = pkg_resources.resource_filename(
            "launchflow", "workflows/tf/resources/aws_codebuild_project/buildspec.yml"
        )
        self._code_build_project = CodeBuildProject(
            f"{name}-codebuild",
            environment=Environment(
                compute_type="BUILD_GENERAL1_SMALL",
                image="aws/codebuild/standard:5.0",
                type="LINUX_CONTAINER",
                image_pull_credentials_type="CODEBUILD",
                environment_variables=[
                    EnvironmentVariable("IMAGE_REPO_NAME", self._ecr.resource_id),
                    EnvironmentVariable("IMAGE_TAG", "latest"),
                    EnvironmentVariable("SOURCE_TAR_NAME", "source.tar.gz"),
                ],
            ),
            build_source=Source(type="NO_SOURCE", buildspec_path=buildspec_path),
            cache=Cache(
                # TODO: Add cache options
                type="NO_CACHE"
            ),
            logs_config=LogsConfig(
                cloud_watch_logs=CloudWatchLogsConfig(
                    status="ENABLED",
                )
            ),
        )
        self._code_build_project.resource_id = resource_id_with_launchflow_prefix
        self._code_build_project.ignore_arguments.add("build_source.buildspec_path")

        if cluster is not None:
            self._manage_ecs_cluster = False
            self._ecs_cluster = cluster
        else:
            self._manage_ecs_cluster = True
            self._ecs_cluster = ECSCluster(f"{name}-cluster")
            self._ecs_cluster.resource_id = resource_id_with_launchflow_prefix

        self._alb = ApplicationLoadBalancer(
            f"{name}-lb", container_port=port, certificate=None  # TODO: Support HTTPS
        )

        self._ecs_fargate_service_container = ECSFargateServiceContainer(
            name,
            ecs_cluster=self._ecs_cluster,
            alb=self._alb,
            desired_count=desired_count,
            port=port,
        )
        self._ecs_fargate_service_container.resource_id = (
            resource_id_with_launchflow_prefix
        )
        self.cpu = cpu
        self.memory = memory
        self.port = port
        self.desired_count = desired_count
        self.dockerfile = dockerfile

    def inputs(self) -> ECSFargateServiceInputs:
        return ECSFargateServiceInputs(
            cpu=self.cpu,
            memory=self.memory,
            port=self.port,
        )

    def resources(self) -> List[Resource]:
        to_return: List[Resource] = [
            self._ecr,
            self._code_build_project,
            self._ecs_fargate_service_container,
            self._alb,
        ]
        if self._manage_ecs_cluster:
            to_return.append(self._ecs_cluster)
        return to_return  # type: ignore

    def outputs(self) -> ServiceOutputs:
        try:
            fargate_outputs = self._ecs_fargate_service_container.outputs()
            alb_outputs = self._alb.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_url = f"http://{alb_outputs.alb_dns_name}"

        service_outputs = ServiceOutputs(
            service_url=service_url,
            # TODO: Support custom domains for ECS Fargate
            dns_outputs=None,
        )
        service_outputs.aws_arn = fargate_outputs.aws_arn

        return service_outputs

    async def _build(
        self,
        *,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> ECSFargateServiceReleaseInputs:
        ecr_outputs = self._ecr.outputs()

        if build_local:
            docker_image = await build_ecr_docker_image_locally(
                dockerfile_path=self.dockerfile,
                build_directory=self.build_directory,
                build_ignore=self.build_ignore,
                build_log_file=build_log_file,
                ecr_repository=ecr_outputs.repository_url,
                launchflow_service_name=self.name,
                launchflow_deployment_id=deployment_id,
                aws_environment_config=aws_environment_config,
            )
        else:
            code_build_outputs = self._code_build_project.outputs()

            docker_image = await build_ecr_docker_image_on_code_build(
                dockerfile_path=self.dockerfile,
                build_directory=self.build_directory,
                build_ignore=self.build_ignore,
                build_log_file=build_log_file,
                ecr_repository=ecr_outputs.repository_url,
                code_build_project_name=code_build_outputs.project_name,
                launchflow_project_name=launchflow_uri.project_name,
                launchflow_environment_name=launchflow_uri.environment_name,
                launchflow_service_name=self.name,
                launchflow_deployment_id=deployment_id,
                aws_environment_config=aws_environment_config,
            )

        return ECSFargateServiceReleaseInputs(docker_image=docker_image)

    async def _promote(
        self,
        *,
        from_aws_environment_config: AWSEnvironmentConfig,
        to_aws_environment_config: AWSEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,  # TODO: Update this service to use the promote_log_file instead of creating a new one
        promote_local: bool,
    ) -> ECSFargateServiceReleaseInputs:
        raise NotImplementedError

    async def _release(
        self,
        *,
        release_inputs: ECSFargateServiceReleaseInputs,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,  # TODO: Update this service to use the release_log_file instead of creating a new one
    ):
        try:
            import boto3
            from botocore.exceptions import WaiterError
        except ImportError:
            raise exceptions.MissingAWSDependency()

        try:
            ecs_cluster_outputs = self._ecs_cluster.outputs()

            ecs_client = boto3.client("ecs", region_name=aws_environment_config.region)

            ecs_service_name = self._ecs_fargate_service_container.resource_id
            task_definition_name = f"{ecs_service_name}-task"

            existing_task_def_response = ecs_client.describe_task_definition(
                taskDefinition=task_definition_name
            )
            new_task_definition = existing_task_def_response["taskDefinition"]
            # Update the Docker image reference in the task definition
            new_task_definition["containerDefinitions"][0][
                "image"
            ] = release_inputs.docker_image
            # Remove the hello world command and entrypoint
            if "command" in new_task_definition["containerDefinitions"][0]:
                del new_task_definition["containerDefinitions"][0]["command"]
            if "entryPoint" in new_task_definition["containerDefinitions"][0]:
                del new_task_definition["containerDefinitions"][0]["entryPoint"]
            # Update the port mappings
            new_task_definition["containerDefinitions"][0]["portMappings"] = [
                {
                    "containerPort": self.port,
                    "hostPort": self.port,
                }
            ]
            # Update the cpu and memory
            service_inputs = self.inputs()
            new_task_definition["cpu"] = str(service_inputs.cpu)
            new_task_definition["memory"] = str(service_inputs.memory)

            # Add the environment variables
            new_task_definition["containerDefinitions"][0]["environment"] = [
                {
                    "name": "LAUNCHFLOW_ARTIFACT_BUCKET",
                    "value": f"s3://{aws_environment_config.artifact_bucket}",
                },
                {"name": "LAUNCHFLOW_PROJECT", "value": launchflow_uri.project_name},
                {
                    "name": "LAUNCHFLOW_ENVIRONMENT",
                    "value": launchflow_uri.environment_name,
                },
                {"name": "LAUNCHFLOW_CLOUD_PROVIDER", "value": "aws"},
                {"name": "LAUNCHFLOW_DEPLOYMENT_ID", "value": deployment_id},
            ]

            # Pulled from: https://stackoverflow.com/questions/69830579/aws-ecs-using-boto3-to-update-a-task-definition
            remove_args = [
                "compatibilities",
                "registeredAt",
                "registeredBy",
                "status",
                "revision",
                "taskDefinitionArn",
                "requiresAttributes",
            ]
            for arg in remove_args:
                new_task_definition.pop(arg, None)

            new_task_definition["tags"] = [
                {"key": "Project", "value": launchflow_uri.project_name},
                {"key": "Environment", "value": launchflow_uri.environment_name},
            ]
            reg_task_def_response = ecs_client.register_task_definition(
                **new_task_definition
            )

            ecs_client.update_service(
                cluster=ecs_cluster_outputs.cluster_name,
                service=ecs_service_name,
                taskDefinition=reg_task_def_response["taskDefinition"][
                    "taskDefinitionArn"
                ],
            )
            # This waiter will wait for the service to reach a steady state. It raises an error after 60 attempts.
            waiter = ecs_client.get_waiter("services_stable")
            try:
                waiter.wait(
                    cluster=ecs_cluster_outputs.cluster_name,
                    services=[ecs_service_name],
                    WaiterConfig={"Delay": 15, "MaxAttempts": 60},
                )
            except WaiterError as e:
                # TODO: Raise a custom exception here
                # TODO: Add a check to see if the task is crash looping, and maybe rollback the task definition
                raise e

        except Exception as e:
            raise exceptions.ServiceReleaseFailed(
                error_message=f"Error releaseing ECS Fargate Service: {str(e)}",
                release_logs_or_link="TODO",
            )
