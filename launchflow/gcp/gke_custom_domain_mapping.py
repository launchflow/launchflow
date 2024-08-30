import dataclasses

from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.resource import GCPResource
from launchflow.gcp.ssl import ManagedSSLCertificate
from launchflow.kubernetes.service_container import ServiceContainer
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs
from launchflow.service import DNSOutputs, DNSRecord


@dataclasses.dataclass
class GKECustomDomainMappingOutputs(Outputs):
    pass


@dataclasses.dataclass
class GKECustomDomainMappingInputs(ResourceInputs):
    ip_address_id: str
    ssl_certificate_id: str
    cluster_id: str
    service_name: str
    namespace: str
    port: int


class GKECustomDomainMapping(GCPResource[GKECustomDomainMappingOutputs]):
    """A resource for mapping a custom domain to a service hosted on GKE.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    ### Example Usage
    """

    product = ResourceProduct.GCP_GKE_CUSTOM_DOMAIN_MAPPING.value

    # TODO: figure out http redirect
    def __init__(
        self,
        name: str,
        *,
        ssl_certificate: ManagedSSLCertificate,
        ip_address: GlobalIPAddress,
        service_container: ServiceContainer,
        service_name: str,
    ) -> None:
        """Create a new CustomDomainMapping resource.

        **Args:**
        - `name` (str): The name of the CustomDomainMapping resource. This must be globally unique.
        - `ssl_certificate (ManagedSSLCertificate):` The [SSL certificate](/reference/gcp-resources/ssl) to use for the domain.
        - `ip_address (GlobalIPAddress)`: The [IP address](/reference/gcp-resources/global-ip-address) to map the domain to.
        """
        super().__init__(
            name=name,
        )
        self.ssl_certificate = ssl_certificate
        self.ip_address = ip_address
        self.service_container = service_container
        self.service_name = service_name

    def inputs(
        self, environment_state: EnvironmentState
    ) -> GKECustomDomainMappingInputs:
        """Get the inputs for the Custom Domain Mapping resource.

        **Args:**
        - `environment_type` (EnvironmentType): The type of environment.

        **Returns:**
        - CustomDomainMappingInputs: The inputs for the Custom Domain Mapping resource.
        """
        return GKECustomDomainMappingInputs(
            resource_id=self.resource_id,
            ip_address_id=Depends(self.ip_address).gcp_id,  # type: ignore
            ssl_certificate_id=Depends(self.ssl_certificate).gcp_id,  # type: ignore
            cluster_id=Depends(self.service_container.cluster).gcp_id,  # type: ignore
            service_name=self.service_name,
            namespace=self.service_container.namespace,
            # TODO: is this the right port?
            port=80,
        )

    def dns_outputs(self) -> DNSOutputs:
        ip_outputs = self.ip_address.outputs()
        ssl_outputs = self.ssl_certificate.outputs()
        return DNSOutputs(
            domain=ssl_outputs.domains[0],
            dns_records=[
                DNSRecord(
                    dns_record_value=ip_outputs.ip_address,
                    dns_record_type="A",
                ),
            ],
        )
