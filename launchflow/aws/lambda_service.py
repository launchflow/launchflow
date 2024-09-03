from dataclasses import dataclass
from typing import List, Optional

import pkg_resources
from typing_extensions import Callable

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.acm import ACMCertificate
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
from launchflow.aws.elastic_ip import ElasticIP
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.nat_gateway import NATGateway
from launchflow.aws.service import AWSDockerServiceOutputs, AWSStaticService
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import StaticServiceOutputs


@dataclass
class LambdaServiceInputs(Inputs):
    pass


class LambdaStaticService(AWSStaticService):
    """TODO"""

    product = ServiceProduct.AWS_STATIC_LAMBDA.value

    def __init__(
        self,
        name: str,
        handler: Callable,
        *,
        static_directory: str = ".",
        static_ignore: List[str] = [],  # type: ignore
        enable_public_access: bool = False,  # TODO: rename this to highlight its for public egress, not ingress
        requirements_txt_path: Optional[str] = None,
        public_route: Optional[str] = None,
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            static_directory=static_directory,
            static_ignore=static_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._api_gateway = None
        if public_route is not None:
            self._api_gateway = lf.aws.APIGateway("tanke-api-gateway")

        self._lambda_service_container = LambdaFunction(
            name, api_gateway=self._api_gateway, route=public_route
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self._elastic_ip = None
        self._nat_gateway = None
        if enable_public_access:
            self._elastic_ip = ElasticIP(f"{name}-elastic-ip")
            self._elastic_ip.resource_id = resource_id_with_launchflow_prefix
            self._nat_gateway = NATGateway(
                f"{name}-nat-gateway", elastic_ip=self._elastic_ip
            )
            self._nat_gateway.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler
        self.requirements_txt_path = requirements_txt_path

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return = [
            self._lambda_service_container,
        ]
        if self._api_gateway:
            to_return.append(self._api_gateway)
        if self._elastic_ip:
            to_return.append(self._elastic_ip)
        if self._nat_gateway:
            to_return.append(self._nat_gateway)
        return to_return  # type: ignore

    def outputs(self) -> StaticServiceOutputs:
        try:
            lambda_outputs = self._lambda_service_container.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_url = "TODO"
        if self._api_gateway is not None:
            try:
                api_gateway_outputs = self._api_gateway.outputs()
                service_url = api_gateway_outputs.api_gateway_endpoint
            except exceptions.ResourceOutputsNotFound:
                raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_outputs = StaticServiceOutputs(
            service_url=service_url,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs


class LambdaDockerService(AWSStaticService):
    """TODO"""

    product = ServiceProduct.AWS_DOCKER_LAMBDA.value

    # TODO: Add better support for custom domains + write up a guide for different domain providers
    def __init__(
        self,
        name: str,
        hack="",
        port: int = 80,
        build_directory: str = ".",
        dockerfile: str = "Dockerfile",
        build_ignore: List[str] = [],
        domain_name: Optional[str] = None,
        certificate: Optional[ACMCertificate] = None,
    ) -> None:
        """TODO"""
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

        self._lambda_service_container = LambdaFunction(
            name,
            port=port,
            hack=hack,
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix
        self.port = port

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return = [
            self._ecr,
            self._code_build_project,
            self._lambda_service_container,
        ]
        if self._https_certificate:
            to_return.append(self._https_certificate)
        return to_return  # type: ignore

    def outputs(self) -> AWSDockerServiceOutputs:
        try:
            ecr_outputs = self._ecr.outputs()
            code_build_outputs = self._code_build_project.outputs()
            lambda_outputs = self._lambda_service_container.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_url = lambda_outputs.lambda_url
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
