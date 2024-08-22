import dataclasses
from typing import Optional

from launchflow.gcp.cloud_run_container import CloudRunServiceContainer
from launchflow.gcp.http_health_check import HttpHealthCheck
from launchflow.gcp.regional_managed_instance_group import RegionalManagedInstanceGroup
from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class CustomDomainMappingOutputs(Outputs):
    ip_address: str
    registered_domain: str
    ssl_certificate_id: str


@dataclasses.dataclass
class GCEServiceBackend:
    managed_instance_group: RegionalManagedInstanceGroup
    health_check: HttpHealthCheck
    named_port: str


@dataclasses.dataclass
class CustomDomainMappingInputs(ResourceInputs):
    domain: str
    cloud_run_service: Optional[str]
    gce_service: Optional[str]
    health_check: Optional[str]
    region: Optional[str]
    named_port: Optional[str]


class CustomDomainMapping(GCPResource[CustomDomainMappingOutputs]):
    """A resource for mapping a custom domain to a Cloud Run service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    ### Example Usage
    ```python
    import launchflow as lf

    custom_domain_mapping = lf.gcp.CustomDomainMapping("my-custom-domain-mapping", domain="my-domain.com", cloud_run=lf.gcp.CloudRunServiceContainer("my-cloud-run-service"))
    ```
    """

    product = ResourceProduct.GCP_CUSTOM_DOMAIN_MAPPING.value

    def __init__(
        self,
        name: str,
        *,
        domain: str,
        cloud_run: Optional[CloudRunServiceContainer] = None,
        gce_service_backend: Optional[GCEServiceBackend] = None,
    ) -> None:
        """Create a new CustomDomainMapping resource.

        **Args:**
        - `name` (str): The name of the CustomDomainMapping resource. This must be globally unique.
        - `domain` (str): The domain to map to the Cloud Run service.
        - `cloud_run` (CloudRunServiceContainer): The Cloud Run service to map the domain to. One and only one of cloud_run and gce_service must be provided.
        - `regional_managed_instance_group` (RegionalManagedInstanceGroup): The Compute Engine service to map the domain to. One and only one of cloud_run and gce_service must be provided.
        """
        super().__init__(
            name=name,
        )
        self.domain = domain
        self.cloud_run = cloud_run
        self.regional_managed_instance_group = gce_service_backend

        if not cloud_run and not gce_service_backend:
            raise ValueError(
                "Either `cloud_run` or `gce_service_backend` must be provided."
            )

        if cloud_run and gce_service_backend:
            raise ValueError(
                "Only one of `cloud_run` or `gce_service_backend` can be provided."
            )

    def inputs(self, environment_state: EnvironmentState) -> CustomDomainMappingInputs:
        """Get the inputs for the Custom Domain Mapping resource.

        **Args:**
        - `environment_type` (EnvironmentType): The type of environment.

        **Returns:**
        - CustomDomainMappingInputs: The inputs for the Custom Domain Mapping resource.
        """
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
            domain=self.domain,
            cloud_run_service=cloud_run,
            gce_service=gce_service,
            health_check=health_check,
            region=region,
            named_port=named_port,
        )
