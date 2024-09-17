import dataclasses
from typing import Optional

from launchflow.gcp.cloud_run_container import CloudRunServiceContainer
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.http_health_check import HttpHealthCheck
from launchflow.gcp.regional_managed_instance_group import RegionalManagedInstanceGroup
from launchflow.gcp.resource import GCPResource
from launchflow.gcp.ssl import ManagedSSLCertificate
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs
from launchflow.service import DNSOutputs, DNSRecord


@dataclasses.dataclass
class CustomDomainMappingOutputs(Outputs):
    pass


@dataclasses.dataclass
class GCEServiceBackend:
    managed_instance_group: RegionalManagedInstanceGroup
    health_check: HttpHealthCheck
    named_port: str


@dataclasses.dataclass
class CustomDomainMappingInputs(ResourceInputs):
    ip_address_id: str
    ssl_certificate_id: str
    cloud_run_service: Optional[str]
    gce_service: Optional[str]
    health_check: Optional[str]
    region: Optional[str]
    named_port: Optional[str]
    include_http_redirect: bool


class CustomDomainMapping(GCPResource[CustomDomainMappingOutputs]):
    """A resource for mapping a custom domain to a Cloud Run service or a compute engine service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    ### Example Usage
    ```python
    import launchflow as lf

    ip_address = lf.gcp.GlobalIPAddress("my-global-ip-address")
    ssl_certificate = lf.gcp.ManagedSSLCertificate("my-ssl-certificate", domains=["example.com"])
    custom_domain_mapping = lf.gcp.CustomDomainMapping(
        "my-custom-domain-mapping",
        ip_address=ip_address,
        ssl_certificate=ssl_certificate,
        cloud_run=lf.gcp.CloudRunServiceContainer("my-cloud-run-service"
    )
    ```
    """

    product = ResourceProduct.GCP_CUSTOM_DOMAIN_MAPPING.value

    def __init__(
        self,
        name: str,
        *,
        ssl_certificate: ManagedSSLCertificate,
        ip_address: GlobalIPAddress,
        cloud_run: Optional[CloudRunServiceContainer] = None,
        gce_service_backend: Optional[GCEServiceBackend] = None,
        include_http_redirect: bool = True,
    ) -> None:
        """Create a new CustomDomainMapping resource.

        **Args:**
        - `name (str)`: The name of the CustomDomainMapping resource. This must be globally unique.
        - `ssl_certificate (ManagedSSLCertificate):` The [SSL certificate](/reference/gcp-resources/ssl) to use for the domain.
        - `ip_address (GlobalIPAddress)`: The [IP address](/reference/gcp-resources/global-ip-address) to map the domain to.
        - `cloud_run (CloudRunServiceContainer)`: The Cloud Run service to map the domain to. One and only one of cloud_run and gce_service must be provided.
        - `regional_managed_instance_group (RegionalManagedInstanceGroup)`: The Compute Engine service to map the domain to. One and only one of cloud_run and gce_service must be provided.
        - `include_http_redirect (bool)`: Whether to include an HTTP redirect to the HTTPS URL. Defaults to True.
        """
        super().__init__(
            name=name,
        )
        self.ssl_certificate = ssl_certificate
        self.ip_address = ip_address
        self.cloud_run = cloud_run
        self.regional_managed_instance_group = gce_service_backend
        self.include_http_redirect = include_http_redirect

        if not cloud_run and not gce_service_backend:
            raise ValueError(
                "Either `cloud_run` or `gce_service_backend` must be provided."
            )

        if cloud_run and gce_service_backend:
            raise ValueError(
                "Only one of `cloud_run` or `gce_service_backend` can be provided."
            )

    def inputs(self, environment_state: EnvironmentState) -> CustomDomainMappingInputs:
        region = None
        if self.cloud_run:
            region = self.cloud_run.region
        if self.regional_managed_instance_group:
            region = self.regional_managed_instance_group.managed_instance_group.region
        cloud_run = None
        if self.cloud_run:
            cloud_run = Depends(self.cloud_run).gcp_id  # type: ignore
        gce_service = None
        health_check = None
        named_port = None
        if self.regional_managed_instance_group:
            gce_service = Depends(
                self.regional_managed_instance_group.managed_instance_group
            ).gcp_id  # type: ignore
            health_check = Depends(
                self.regional_managed_instance_group.health_check
            ).gcp_id  # type: ignore
            named_port = self.regional_managed_instance_group.named_port
        return CustomDomainMappingInputs(
            resource_id=self.resource_id,
            ip_address_id=Depends(self.ip_address).gcp_id,  # type: ignore
            ssl_certificate_id=Depends(self.ssl_certificate).gcp_id,  # type: ignore
            cloud_run_service=cloud_run,
            gce_service=gce_service,
            health_check=health_check,
            region=region,
            named_port=named_port,
            include_http_redirect=self.include_http_redirect,
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
