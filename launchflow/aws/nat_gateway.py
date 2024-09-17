from dataclasses import dataclass
from typing import Optional

import launchflow as lf
from launchflow.aws.elastic_ip import ElasticIP
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclass
class PrivateRouteConfig(Inputs):
    destination_cidr_block: str


# TODO: Expose more options for NATGateway
@dataclass
class NATGatewayInputs(ResourceInputs):
    eip_allocation_id: str
    private_route_config: Optional[PrivateRouteConfig]


@dataclass
class NATGatewayOutputs(Outputs):
    nat_gateway_id: str


class NATGateway(AWSResource[NATGatewayOutputs]):
    """A NAT Gateway

    ### Example Usage
    ```python
    import launchflow as lf

    nat = lf.aws.NATGateway("my-nat-gateway")
    ```
    """

    product = ResourceProduct.AWS_NAT_GATEWAY.value

    def __init__(
        self,
        name: str,
        *,
        elastic_ip: ElasticIP,
        private_route_config: Optional[PrivateRouteConfig] = PrivateRouteConfig(
            destination_cidr_block="0.0.0.0/0"
        ),
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.elastic_ip = elastic_ip
        self.private_route_config = private_route_config

        self.depends_on(self.elastic_ip)

    def inputs(self, environment_state: EnvironmentState) -> NATGatewayInputs:
        eip_allocation_id = Depends(self.elastic_ip).allocation_id  # type: ignore
        return NATGatewayInputs(
            resource_id=self.resource_id,
            eip_allocation_id=eip_allocation_id,
            private_route_config=self.private_route_config,
        )
