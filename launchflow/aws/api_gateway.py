from dataclasses import dataclass
from typing import Literal, Optional

import launchflow as lf
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.resource import AWSResource
from launchflow.aws.shared import CORS
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


# TODO: Expose more options for APIGateway
@dataclass
class APIGatewayInputs(ResourceInputs):
    protocol_type: Literal["HTTP", "WEBSOCKET"]
    cors: Optional[CORS]


@dataclass
class APIGatewayOutputs(Outputs):
    api_gateway_id: str
    api_gateway_endpoint: str


class APIGateway(AWSResource[APIGatewayOutputs]):
    """An API Gateway

    ### Example Usage
    ```python
    import launchflow as lf

    nat = lf.aws.APIGateway("my-api-gateway")
    ```
    """

    product = ResourceProduct.AWS_API_GATEWAY.value

    def __init__(
        self,
        name: str,
        *,
        # NOTE: We don't support WEBSOCKET protocol type yet
        protocol_type: Literal["HTTP"] = "HTTP",
        cors: Optional[CORS] = None,
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.protocol_type = protocol_type
        self.cors = cors

    def inputs(self, environment_state: EnvironmentState) -> APIGatewayInputs:
        return APIGatewayInputs(
            resource_id=self.resource_id,
            protocol_type=self.protocol_type,
            cors=self.cors,
        )

    # TODO: add builder pattern API for adding routes. Requires Resource.subresources()
    def add_route(self, path: str) -> None:
        raise NotImplementedError


@dataclass
class APIGatewayLambdaIntegrationInputs(ResourceInputs):
    api_gateway_id: str
    function_arn: str
    function_alias: str


@dataclass
class APIGatewayLambdaIntegrationOutputs(Outputs):
    api_integration_id: str


class APIGatewayLambdaIntegration(AWSResource[APIGatewayLambdaIntegrationOutputs]):
    """An API Gateway Integration

    ### Example Usage
    ```python
    import launchflow as lf

    api_gateway = lf.aws.APIGateway("my-api-gateway")
    function = lf.aws.LambdaFunction("my-lambda-function")
    integration = lf.aws.APIGatewayLambdaIntegrationOutputs(
        "my-api-gateway-route",
        api_gateway=api_gateway,
        function=function,
    )
    ```
    """

    product = ResourceProduct.AWS_API_GATEWAY_LAMBDA_INTEGRATION.value

    def __init__(
        self,
        name: str,
        *,
        api_gateway: APIGateway,
        # NOTE: This only supports Lambda function integrations for now
        function: LambdaFunction,
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self._api_gateway = api_gateway
        self._function = function
        self.depends_on(
            api_gateway, function
        )  # TODO: Remove this once we fix lf.node.Depends

    def inputs(
        self, environment_state: EnvironmentState
    ) -> APIGatewayLambdaIntegrationInputs:
        return APIGatewayLambdaIntegrationInputs(
            resource_id=self.resource_id,
            api_gateway_id=Depends(self._api_gateway).api_gateway_id,  # type: ignore
            function_arn=Depends(self._function).aws_arn,  # type: ignore
            function_alias=Depends(self._function).alias_name,  # type: ignore
        )


# TODO: Expose more options for APIGatewayRoute
@dataclass
class APIGatewayRouteInputs(ResourceInputs):
    api_gateway_id: str
    route_key: str
    authorization: Literal["NONE", "AWS_IAM", "JWT", "CUSTOM"]
    api_integration_id: Optional[str]


@dataclass
class APIGatewayRouteOutputs(Outputs):
    api_route_id: str


class APIGatewayRoute(AWSResource[APIGatewayRouteOutputs]):
    """An API Gateway Route

    ### Example Usage
    ```python
    import launchflow as lf

    api_gateway = lf.aws.APIGateway("my-api-gateway")
    route = lf.aws.APIGatewayRoute("my-api-gateway-route", api_gateway=api_gateway)
    ```
    """

    product = ResourceProduct.AWS_API_GATEWAY_ROUTE.value

    def __init__(
        self,
        name: str,
        *,
        api_gateway: APIGateway,
        route_key: str = "$default",
        # NOTE: We don't support JWT or CUSTOM authorization yet
        authorization: Literal["NONE", "AWS_IAM"] = "NONE",  # NONE == public
        api_gateway_integration: Optional[APIGatewayLambdaIntegration] = None,
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self._api_gateway = api_gateway
        self.depends_on(api_gateway)  # TODO: Remove this once we fix lf.node.Depends
        self._api_gateway_integration = api_gateway_integration
        if api_gateway_integration is not None:
            self.depends_on(  # TODO: Remove this once we fix lf.node.Depends
                api_gateway_integration
            )

        self.route_key = route_key
        self.authorization = authorization

    def inputs(self, environment_state: EnvironmentState) -> APIGatewayRouteInputs:
        api_integration_id = None
        if self._api_gateway_integration is not None:
            api_integration_id = Depends(
                self._api_gateway_integration
            ).api_integration_id  # type: ignore

        return APIGatewayRouteInputs(
            resource_id=self.resource_id,
            api_gateway_id=Depends(self._api_gateway).api_gateway_id,  # type: ignore
            route_key=self.route_key,
            authorization=self.authorization,  # type: ignore
            api_integration_id=api_integration_id,
        )
