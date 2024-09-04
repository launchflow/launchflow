from dataclasses import dataclass
from typing import List, Optional

from typing_extensions import Callable

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.acm import ACMCertificate
from launchflow.aws.elastic_ip import ElasticIP
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.lambda_layer import PythonLambdaLayer
from launchflow.aws.nat_gateway import NATGateway
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
        # TODO: Add a `domain` parameter that can be a string or a composite resource class
        domain: Optional[str] = None,
        python_packages: Optional[List[str]] = None,
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            static_directory=static_directory,
            static_ignore=static_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._api_gateway = lf.aws.APIGateway("tanke-api-gateway")

        self.layers = None
        if python_packages is not None:
            self.layers = []
            for package in python_packages:
                package_name_no_extras = package.split("[")[0]
                layer = PythonLambdaLayer(
                    f"{package_name_no_extras}-layer", packages=[package]
                )
                self.layers.append(layer)

        self._lambda_service_container = LambdaFunction(
            name, api_gateway=self._api_gateway, route=route, layers=self.layers
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler
        self.requirements_txt_path = requirements_txt_path

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return = [
            self._lambda_service_container,
            self._api_gateway,
        ]
        if self.layers:
            to_return.extend(self.layers)
        return to_return  # type: ignore

    def outputs(self) -> StaticServiceOutputs:
        try:
            lambda_outputs = self._lambda_service_container.outputs()
            api_gateway_outputs = self._api_gateway.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_outputs = StaticServiceOutputs(
            service_url=api_gateway_outputs.api_gateway_endpoint,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs


class LambdaDockerService(AWSDockerService):
    """TODO"""

    product = ServiceProduct.AWS_DOCKER_LAMBDA.value

    def __init__(
        self,
        name: str,
        handler: Callable,
        *,
        port: int = 80,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],
        route: str = "/",
        # TODO: Add a `domain` parameter that can be a string or a composite resource class
        domain: Optional[str] = None,
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._api_gateway = lf.aws.APIGateway("tanke-api-gateway")

        self._lambda_service_container = LambdaFunction(
            name,
            api_gateway=self._api_gateway,
            route=route,
            package_type="Image",
        )
        self._lambda_service_container.resource_id = resource_id_with_launchflow_prefix

        self.handler = handler
        self.port = port

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return = [
            self._lambda_service_container,
            self._api_gateway,
        ]
        return to_return  # type: ignore

    def outputs(self) -> StaticServiceOutputs:
        try:
            lambda_outputs = self._lambda_service_container.outputs()
            api_gateway_outputs = self._api_gateway.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_outputs = StaticServiceOutputs(
            service_url=api_gateway_outputs.api_gateway_endpoint,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs
