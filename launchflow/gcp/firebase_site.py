from dataclasses import dataclass
from typing import List, Optional

from launchflow import exceptions
from launchflow.gcp.firebase import FirebaseHostingSite, FirebaseProject
from launchflow.gcp.service import GCPService
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DNSOutputs, DNSRecord, ServiceOutputs


@dataclass
class FirebaseStaticSiteInputs(Inputs):
    pass


class FirebaseStaticSite(GCPService):
    """A service hosted on Firebase Hosting.

    ### Example Usage
    ```python
    import launchflow as lf

    website = lf.gcp.FirebaseStaticSite("my-website", build_directory="path/to/local/files")
    ```
    """

    product = ServiceProduct.GCP_FIREBASE_STATIC_SITE.value

    def __init__(
        self,
        name: str,
        # static inputs
        build_directory: str,
        *,
        build_ignore: List[str] = [],
        # backend bucket inputs
        region: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Creates a new Cloud Run service.

        **Args:**
        - `name (str)`: The name of the service.
        - `build_directory (str)`: The directory of static files to serve. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when deploying the service. This can be in the same syntax you would use for a `.gitignore`.
        - `region (Optional[str])`: The region to deploy the service to.
        - `domain (Optional[str])`: The custom domain to map to the service.
        """
        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        self.region = region
        self.domain = domain

        # TODO: make this configurable
        self._firebase_project = FirebaseProject(name=f"{name}-firebase-project")
        self._firebase_hosting_site = FirebaseHostingSite(
            name=f"{name}-firebase-site",
            firebase_project=self._firebase_project,
            custom_domain=domain,
        )

    def inputs(self) -> FirebaseStaticSiteInputs:
        return FirebaseStaticSiteInputs()

    def resources(self) -> List[Resource]:
        return [
            self._firebase_project,
            self._firebase_hosting_site,
        ]

    def outputs(self) -> ServiceOutputs:
        try:
            firebase_hosting_outputs = self._firebase_hosting_site.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        dns_outputs = None
        if firebase_hosting_outputs.desired_dns_records and self.domain is not None:
            dns_records = []
            for record in firebase_hosting_outputs.desired_dns_records:
                dns_type, dns_value = record.split(",", 1)
                dns_records.append(
                    DNSRecord(
                        dns_record_value=dns_value,
                        dns_record_type=dns_type,  # type: ignore
                    ),
                )
            dns_outputs = DNSOutputs(
                domain=self.domain,
                dns_records=dns_records,
            )

        service_url = firebase_hosting_outputs.default_url
        if self.domain:
            service_url = f"https://{self.domain}"

        service_outputs = ServiceOutputs(
            service_url=service_url,
            dns_outputs=dns_outputs,
        )
        service_outputs.gcp_id = firebase_hosting_outputs.gcp_id

        return service_outputs
