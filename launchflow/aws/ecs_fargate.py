from dataclasses import dataclass
from typing import List, Optional

import pkg_resources

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.acm import ACMCertificate
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
from launchflow.aws.service import AWSDockerService, AWSDockerServiceOutputs
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource


@dataclass
class ECSFargateInputs(Inputs):
    cpu: int = 256
    memory: int = 512


class ECSFargate(AWSDockerService):
    """A service hosted on AWS ECS Fargate.

    Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html).


    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to an ECS Fargate Service in your AWS account
    service = lf.aws.ECSFargate("my-service")
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
        dockerfile: str = "Dockerfile",
        build_ignore: List[str] = [],
        domain: Optional[str] = None,
        certificate: Optional[ACMCertificate] = None,
    ) -> None:
        """Creates a new ECS Fargate service.

        **Args:**
        - `name (str)`: The name of the service.
        - `ecs_cluster (Union[ECSCluster, str])`: The ECS cluster or the name of the ECS cluster.
        - `cpu (int)`: The CPU units to allocate to the container. Defaults to 256.
        - `memory (int)`: The memory to allocate to the container. Defaults to 512.
        - `port (int)`: The port the container listens on. Defaults to 80.
        - `desired_count (int)`: The number of tasks to run. Defaults to 1.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `domain (Optional[str])`: The domain name to use for the service. This will create an ACM certificate and configure the ALB to use HTTPS.
        """
        if domain is not None and certificate is not None:
            raise ValueError(
                "You cannot specify both a domain and a certificate. Please choose one."
            )
        super().__init__(
            name=name,
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
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

        self._ecs_cluster = ECSCluster(f"{name}-cluster")
        self._ecs_cluster.resource_id = resource_id_with_launchflow_prefix

        self._https_certificate = None
        if domain:
            self._https_certificate = ACMCertificate(f"{name}-certificate", domain)
        if certificate:
            self._https_certificate = certificate
        self._alb = ApplicationLoadBalancer(
            f"{name}-lb", container_port=port, certificate=self._https_certificate
        )

        self._ecs_fargate_service_container = ECSFargateServiceContainer(
            name,
            self._ecs_cluster,
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

    def inputs(self) -> ECSFargateInputs:
        return ECSFargateInputs(
            cpu=self.cpu,
            memory=self.memory,
        )

    def resources(self) -> List[Resource]:
        to_return = [
            self._ecr,
            self._code_build_project,
            self._ecs_cluster,
            self._ecs_fargate_service_container,
            self._alb,
        ]
        if self._https_certificate:
            to_return.append(self._https_certificate)
        return to_return  # type: ignore

    def outputs(self) -> AWSDockerServiceOutputs:
        try:
            ecr_outputs = self._ecr.outputs()
            code_build_outputs = self._code_build_project.outputs()
            fargate_outputs = self._ecs_fargate_service_container.outputs()
            alb_outputs = self._alb.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_url = f"http://{alb_outputs.alb_dns_name}"
        if self._https_certificate:
            domain = self._https_certificate.outputs().domain_name
            service_url = f"https://{domain}"

        service_outputs = AWSDockerServiceOutputs(
            service_url=service_url,
            docker_repository=ecr_outputs.repository_url,
            code_build_project_name=code_build_outputs.project_name,
            # TODO: Support custom domains for ECS Fargate
            dns_outputs=None,
        )
        service_outputs.aws_arn = fargate_outputs.aws_arn

        return service_outputs
