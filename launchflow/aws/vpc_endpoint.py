import dataclasses
from typing import Literal

from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class VPCEndpointOutputs(Outputs):
    pass


@dataclasses.dataclass
class VPCEndpointInputs(ResourceInputs):
    service_name: str
    endpoint_type: Literal["Gateway", "Interface"]


class VPCEndpoint(AWSResource[VPCEndpointOutputs]):
    """An AWS VPC Endpoint resource.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html).

    ### Example Usage
    ```python
    import launchflow as lf

    # Connects your private VPC subnets to the S3 service.
    s3_connect = lf.aws.S3Bucket("my-bucket", service_name="com.amazonaws.us-east-1.s3", endpoint_type="Gateway")
    ecr_dkr_connect = lf.aws.VPCEndpoint("my-bucket", service_name="com.amazonaws.us-east-1.ecr.dkr", endpoint_type="Interface")
    ec_api_connect = lf.aws.VPCEndpoint("my-bucket", service_name="com.amazonaws.us-east-1.ec2", endpoint_type="Interface")
    ```
    """

    product = ResourceProduct.AWS_VPC_ENDPOINT.value

    def __init__(
        self,
        name: str,
        *,
        service_name: str,
        endpoint_type: Literal["Gateway", "Interface"],
    ) -> None:
        """Create a new VPC endpoint resource.

        **Args:**
        - `name (str)`: The name of the bucket. This must be globally unique.
        - `service_name (str)`: The name of the service to connect to.
        - `endpoint_type (Literal["Gateway", "Interface"])`: The type of VPC endpoint to create.
        """
        super().__init__(name=name)
        self.service_name = service_name
        self.endpoint_type: Literal["Gateway", "Interface"] = endpoint_type

    def inputs(self, environment_state: EnvironmentState) -> VPCEndpointInputs:
        return VPCEndpointInputs(
            resource_id=self.resource_id,
            service_name=self.service_name,
            endpoint_type=self.endpoint_type,
        )
