from dataclasses import dataclass
from typing import List, Optional

from typing_extensions import Callable

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.acm import ACMCertificate
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.service import (
    AWSDockerService,
    AWSDockerServiceOutputs,
    AWSStaticService,
)
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
        requirements_txt_path: Optional[str] = None,
        route: str = "/",
        timeout: int = 10,
        # TODO: Add a `domain` parameter that can be a string or a composite resource class
        domain: Optional[str] = None,
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            static_directory=static_directory,
            static_ignore=static_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._api_gateway = lf.aws.APIGateway(f"{name}-api")

        self._lambda_service_container = LambdaFunction(
            name,
            api_gateway=self._api_gateway,
            route=route,
            timeout=timeout,
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler
        self.requirements_txt_path = requirements_txt_path

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        return [self._lambda_service_container, self._api_gateway]

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


class LambdaDockerService(AWSDockerService):
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
        raise NotImplementedError

    def inputs(self) -> LambdaServiceInputs:
        raise NotImplementedError

    def resources(self) -> List[Resource]:
        raise NotImplementedError

    def outputs(self) -> AWSDockerServiceOutputs:
        raise NotImplementedError
