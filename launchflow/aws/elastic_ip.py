from dataclasses import dataclass
from typing import Literal, Optional, Union

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


# TODO: Expose more options for Elastic IP
@dataclass
class ElasticIPInputs(ResourceInputs):
    domain: Union[None, Literal["vpc"]]


@dataclass
class ElasticIPOutputs(Outputs):
    allocation_id: str
    public_ip: str
    private_ip: Optional[str]


class ElasticIP(AWSResource[ElasticIPOutputs]):
    """An Elastic IP address.

    ### Example Usage
    ```python
    import launchflow as lf

    static_ip = lf.aws.ElasticIP("my-static-ip")
    ```
    """

    product = ResourceProduct.AWS_ELASTIC_IP.value

    def __init__(
        self,
        name: str,
        *,
        domain: Union[None, Literal["vpc"]] = "vpc",
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.domain = domain

    def inputs(self, environment_state: EnvironmentState) -> ElasticIPInputs:
        return ElasticIPInputs(
            resource_id=self.resource_id,
            domain=self.domain,
        )
