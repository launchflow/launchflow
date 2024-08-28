import dataclasses

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class GlobalIPAddressOutputs(Outputs):
    ip_address: str


@dataclasses.dataclass
class GlobalIPAddressInputs(ResourceInputs):
    pass


class GlobalIPAddress(GCPResource[GlobalIPAddressOutputs]):
    """
    A global ip address resource.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/compute/docs/ip-addresses).

    ### Example Usage
    ```python
    import launchflow as lf

    ip = lf.gcp.GlobalIPAddress("ip-addres")
    ```
    """

    product = ResourceProduct.GCP_GLOBAL_IP_ADDRESS.value

    def __init__(self, name: str) -> None:
        """Create a new Global IP Address resource.

        **Args:**
        - `name (str)`: The name of the ip address.
        """
        super().__init__(name=name)

    def inputs(self, environment_state: EnvironmentState) -> GlobalIPAddressInputs:
        return GlobalIPAddressInputs(resource_id=self.resource_id)
