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
from launchflow.aws.lambda_container import LambdaServiceContainer
from launchflow.aws.service import AWSDockerService, AWSDockerServiceOutputs
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource


@dataclass
class LambdaServiceInputs(Inputs):
    pass
    # cpu: int = 256
    # memory: int = 512
    # port: int = 80
    # desired_count: int = 1


class LambdaService(AWSDockerService):
    """TODO
    """

    product = ServiceProduct.AWS_LAMBDA.value

    # TODO: Add better support for custom domains + write up a guide for different domain providers
    def __init__(
        self,
        name: str,
        hack = "",
        port: int = 80,
        build_directory: str = ".",
        dockerfile: str = "Dockerfile",
        build_ignore: List[str] = [],
        domain_name: Optional[str] = None,
        certificate: Optional[ACMCertificate] = None,
    ) -> None:
        """TODO
        """
        if domain_name is not None and certificate is not None:
            raise ValueError(
                "You cannot specify both a domain_name and a certificate. Please choose one."
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

        self._https_certificate = None
        if domain_name:
            self._https_certificate = ACMCertificate(f"{name}-certificate", domain_name)
        if certificate:
            self._https_certificate = certificate
        self._alb = ApplicationLoadBalancer(
            f"{name}-lb", container_port=port, certificate=self._https_certificate
        )

        self._lambda_service_container = LambdaServiceContainer(
            name,
            alb=self._alb,
            port=port,
            hack=hack,
        )
        self._lambda_service_container.resource_id = (
            resource_id_with_launchflow_prefix
        )
        self.port = port

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return = [
            self._ecr,
            self._code_build_project,
            self._lambda_service_container,
            self._alb,
        ]
        if self._https_certificate:
            to_return.append(self._https_certificate)
        return to_return  # type: ignore

    def outputs(self) -> AWSDockerServiceOutputs:
        try:
            ecr_outputs = self._ecr.outputs()
            code_build_outputs = self._code_build_project.outputs()
            lambda_outputs = self._lambda_service_container.outputs()
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
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs
