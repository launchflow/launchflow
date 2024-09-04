from dataclasses import dataclass
from typing import Literal

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


# TODO: Expose more options for APIGateway
@dataclass
class APIGatewayInputs(ResourceInputs):
    protocol_type: Literal["HTTP", "WEBSOCKET"]


@dataclass
class APIGatewayOutputs(Outputs):
    api_gateway_id: str
    api_gateway_endpoint: str


class APIGateway(AWSResource[APIGatewayOutputs]):
    """An API Gateway

    ****Example usage:****
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
        protocol_type: Literal["HTTP", "WEBSOCKET"] = "HTTP",
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.protocol_type = protocol_type

    def inputs(self, environment_state: EnvironmentState) -> APIGatewayInputs:
        """Get the inputs required for the API Gateway.

        **Args:**
         - `environment_state (EnvironmentState)`: The environment to get inputs for

        **Returns:**
         - `APIGatewayInputs`: The inputs required for the API Gateway
        """

        return APIGatewayInputs(
            resource_id=self.resource_id,
            protocol_type=self.protocol_type,
        )
