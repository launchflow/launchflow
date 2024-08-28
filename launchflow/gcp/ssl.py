import dataclasses
from typing import List, Union

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class ManagedSSLCertificateOutputs(Outputs):
    domains: List[str]


@dataclasses.dataclass
class ManagedSSLCertificateInputs(ResourceInputs):
    domains: List[str]


class ManagedSSLCertificate(GCPResource[ManagedSSLCertificateOutputs]):
    """
    A manage ssl certificate resource.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs).

    ### Example Usage
    ```python
    import launchflow as lf

    ip = lf.gcp.GlobalIPAddress("ip-addres")
    ```
    """

    product = ResourceProduct.GCP_MANAGED_SSL_CERTIFICATE.value

    def __init__(self, name: str, domains: Union[List[str], str]) -> None:
        """Create a new managed ssl certificate resource.

        **Args:**
        - `name (str)`: The name of the ip address.
        - `domain (str)`: The domain of the ssl certificate.
        """
        super().__init__(name=name)
        self.domains = []
        if isinstance(domains, str):
            self.domains.append(domains)
        else:
            self.domains = domains
            self.domains.sort()

    def inputs(
        self, environment_state: EnvironmentState
    ) -> ManagedSSLCertificateInputs:
        return ManagedSSLCertificateInputs(
            resource_id=self.resource_id, domains=self.domains
        )
