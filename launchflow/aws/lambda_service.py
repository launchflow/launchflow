from dataclasses import dataclass
from typing import List, Optional, Union

import pkg_resources
from typing_extensions import Callable

import launchflow as lf
from launchflow import exceptions
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
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.service import AWSDockerService, AWSDockerServiceOutputs, AWSService
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs


@dataclass
class LambdaServiceInputs(Inputs):
    pass


class LambdaService(AWSService):
    """TODO"""

    product = ServiceProduct.AWS_LAMBDA.value

    def __init__(
        self,
        name: str,
        *,
        handler: Union[str, Callable],  # type: ignore
        route: str = "/",
        timeout_seconds: int = 10,
        domain: Optional[str] = None,
        requirements_txt_path: Optional[str] = None,
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._api_gateway = lf.aws.APIGateway(f"{name}-api")

        self._lambda_service_container = LambdaFunction(
            name,
            api_gateway=self._api_gateway,
            route=route,
            timeout=timeout_seconds,
            package_type="Zip",
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler
        self.requirements_txt_path = requirements_txt_path

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        return [self._lambda_service_container, self._api_gateway]

    def outputs(self) -> ServiceOutputs:
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

        service_outputs = ServiceOutputs(
            service_url=service_url,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs


class LambdaDockerService(AWSDockerService):
    """TODO"""

    product = ServiceProduct.AWS_DOCKER_LAMBDA.value

    # TODO: Add better support for custom domains + write up a guide for different domain providers
    def __init__(
        self,
        name: str,
        *,
        handler: Union[str, Callable],  # type: ignore
        route: str = "/",
        timeout_seconds: int = 10,
        domain: Optional[str] = None,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

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

        self._api_gateway = lf.aws.APIGateway(f"{name}-api")

        self._lambda_service_container = LambdaFunction(
            name,
            api_gateway=self._api_gateway,
            route=route,
            timeout=timeout_seconds,
            package_type="Image",
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler

    def inputs(self) -> LambdaServiceInputs:
        raise NotImplementedError

    def resources(self) -> List[Resource]:
        return [
            self._ecr,
            self._code_build_project,
            self._lambda_service_container,
            self._api_gateway,
        ]

    def outputs(self) -> AWSDockerServiceOutputs:
        try:
            ecr_outputs = self._ecr.outputs()
            code_build_outputs = self._code_build_project.outputs()
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

        service_outputs = AWSDockerServiceOutputs(
            service_url=service_url,
            docker_repository=ecr_outputs.repository_url,
            code_build_project_name=code_build_outputs.project_name,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs
