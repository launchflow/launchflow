from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from launchflow import exceptions
from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.cloud_run_container import CloudRunServiceContainer
from launchflow.gcp.custom_domain_mapping import CustomDomainMapping
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.service import GCPDockerService
from launchflow.gcp.ssl import ManagedSSLCertificate
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DockerServiceOutputs


@dataclass
class CloudRunInputs(Inputs):
    pass


class CloudRunService(GCPDockerService):
    """A service hosted on GCP Cloud Run.

    ### Example Usage

    #### Basic Usage
    ```python
    import launchflow as lf

    service = lf.gcp.CloudRunService("my-service", cpu=4)
    ```

    #### Custom Environment Variables
    ```python
    import launchflow as lf

    service = lf.gcp.CloudRunService(
        "my-service",
        environment_variables={"MY_ENV_VAR": "my-value"}
    )
    ```

    **NOTE:** This will create the following infrastructure in your GCP project:
    - A [Cloud Run](https://cloud.google.com/run) service with the specified configuration.
    - A [Load Balancer](https://cloud.google.com/load-balancing) to route traffic to the service.
    - A [Cloud Build](https://cloud.google.com/build) trigger that builds and deploys the service.
    - An [Artifact Registry](https://cloud.google.com/artifact-registry) repository to store the service's Docker image.
    """

    product = ServiceProduct.GCP_CLOUD_RUN.value

    def __init__(
        self,
        name: str,
        # build inputs
        build_directory: str = ".",
        build_ignore: List[str] = [],
        dockerfile: str = "Dockerfile",
        # cloud run inputs
        region: Optional[str] = None,
        cpu: Optional[int] = None,
        memory: Optional[str] = None,
        port: Optional[int] = None,
        # TODO: don't think this needs to be optional, and the docstring says it defaults to true, which is only true if the default is in cloud run or somewhere downstream in our code
        publicly_accessible: Optional[bool] = None,
        min_instance_count: Optional[int] = None,
        max_instance_count: Optional[int] = None,
        max_instance_request_concurrency: Optional[int] = None,
        invokers: Optional[List[str]] = None,
        custom_audiences: Optional[List[str]] = None,
        ingress: Optional[
            Literal[
                "INGRESS_TRAFFIC_ALL",
                "INGRESS_TRAFFIC_INTERNAL_ONLY",
                "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
            ]
        ] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        # custom domain inputs
        domain: Optional[str] = None,
    ) -> None:
        """Creates a new Cloud Run service.

        **Args:**
        - `name (str)`: The name of the service.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `region (Optional[str])`: The region to deploy the service to.
        - `cpu (Optional[int])`: The number of CPUs to allocate to each instance of the service.
        - `memory (Optional[str])`: The amount of memory to allocate to each instance of the service.
        - `port (Optional[int])`: The port the service listens on.
        - `publicly_accessible (Optional[bool])`: Whether the service is publicly accessible. Defaults to True.
        - `min_instance_count (Optional[int])`: The minimum number of instances to keep running.
        - `max_instance_count (Optional[int])`: The maximum number of instances to run.
        - `max_instance_request_concurrency (Optional[int])`: The maximum number of requests each instance can handle concurrently.
        - `invokers (Optional[List[str]])`: A list of invokers that can access the service.
        - `custom_audiences (Optional[List[str]])`: A list of custom audiences that can access the service. See: [https://cloud.google.com/run/docs/configuring/custom-audiences](https://cloud.google.com/run/docs/configuring/custom-audiences).
        - `ingress (Optional[Literal["INGRESS_TRAFFIC_ALL", "INGRESS_TRAFFIC_INTERNAL_ONLY", "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"]])`: The ingress settings for the service. See: [https://cloud.google.com/run/docs/securing/ingress](https://cloud.google.com/run/docs/configuring/custom-audiences).
        - `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set for the service.
        - `domain (Optional[str])`: The custom domain to map to the service.
        """
        super().__init__(
            name=name,
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        self.region = region
        self.cpu = cpu
        self.memory = memory
        self.port = port
        self.publicly_accessible = publicly_accessible
        self.min_instance_count = min_instance_count
        self.max_instance_count = max_instance_count
        self.max_instance_request_concurrency = max_instance_request_concurrency
        self.invokers = invokers
        self.custom_audiences = custom_audiences
        self.ingress = ingress

        # Resources - flows should not access these directly
        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER, location=region
        )
        self._artifact_registry.resource_id = name
        self._cloud_run_service_container = CloudRunServiceContainer(
            f"{name}-container",
            region=region,
            cpu=cpu,
            memory=memory,
            port=port,
            publicly_accessible=publicly_accessible,
            min_instance_count=min_instance_count,
            max_instance_count=max_instance_count,
            max_instance_request_concurrency=max_instance_request_concurrency,
            invokers=invokers,
            custom_audiences=custom_audiences,
            ingress=ingress,
            environment_variables=environment_variables,
        )
        self._cloud_run_service_container.resource_id = name

        self._custom_domain_mapping: Optional[CustomDomainMapping] = None
        self._ip_address: Optional[GlobalIPAddress] = None
        self._ssl_certificate: Optional[ManagedSSLCertificate] = None

        if domain:
            self._ip_address = GlobalIPAddress(f"{name}-ip-address")
            self._ssl_certificate = ManagedSSLCertificate(
                f"{name}-ssl-certificate", domains=domain
            )
            self._custom_domain_mapping = CustomDomainMapping(
                f"{name}-domain-mapping",
                ip_address=self._ip_address,
                ssl_certificate=self._ssl_certificate,
                cloud_run=self._cloud_run_service_container,
            )
            self._custom_domain_mapping.resource_id = name

    def inputs(self) -> CloudRunInputs:
        return CloudRunInputs()

    def resources(self) -> List[Resource]:
        to_return: List[Resource] = [
            self._artifact_registry,
            self._cloud_run_service_container,
        ]
        if self._ip_address is not None:
            to_return.append(self._ip_address)
        if self._ssl_certificate is not None:
            to_return.append(self._ssl_certificate)
        if self._custom_domain_mapping is not None:
            to_return.append(self._custom_domain_mapping)
        return to_return

    def outputs(self) -> DockerServiceOutputs:
        try:
            service_container_outputs = self._cloud_run_service_container.outputs()
            artifact_registry_outputs = self._artifact_registry.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        dns_outputs = None
        if self._custom_domain_mapping:
            dns_outputs = self._custom_domain_mapping.dns_outputs()

        if artifact_registry_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")

        service_outputs = DockerServiceOutputs(
            service_url=service_container_outputs.service_url,
            docker_repository=artifact_registry_outputs.docker_repository,
            dns_outputs=dns_outputs,
        )
        service_outputs.gcp_id = service_container_outputs.gcp_id

        return service_outputs
