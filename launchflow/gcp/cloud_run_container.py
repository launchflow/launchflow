from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

import launchflow as lf
from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class CloudRunServiceContainerInputs(ResourceInputs):
    region: Optional[str]
    cpu: Optional[int]
    memory: Optional[str]
    port: Optional[int]
    publicly_accessible: Optional[bool]
    min_instance_count: Optional[int]
    max_instance_count: Optional[int]
    max_instance_request_concurrency: Optional[int]
    invokers: Optional[List[str]]
    custom_audiences: Optional[List[str]]
    ingress: Optional[
        Literal[
            "INGRESS_TRAFFIC_ALL",
            "INGRESS_TRAFFIC_INTERNAL_ONLY",
            "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
        ]
    ]
    launchflow_environment: str
    launchflow_project: str
    environment_variables: Optional[Dict[str, str]]


@dataclass
class CloudRunServiceContainerOutputs(Outputs):
    service_url: str


class CloudRunServiceContainer(GCPResource[CloudRunServiceContainerOutputs]):
    """A container for a service running on Cloud Run.

    ### Example usage
    ```python
    import launchflow as lf

    service_container = lf.gcp.CloudRunServiceContainer("my-service-container", cpu=4)
    ```
    """

    product = ResourceProduct.GCP_CLOUD_RUN_SERVICE_CONTAINER.value

    def __init__(
        self,
        name: str,
        region: Optional[str] = None,
        cpu: Optional[int] = None,
        memory: Optional[str] = None,
        port: Optional[int] = None,
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
    ) -> None:
        """Creates a new Cloud Run Service container.

        **Args:**
        - `name (str)`: The name of the service.
        - `region (Optional[str])`: The region to deploy the service to.
        - `cpu (Optional[int])`: The number of CPUs to allocate to each instance of the service.
        - `memory (Optional[str])`: The amount of memory to allocate to each instance of the service.
        - `port (Optional[int])`: The port the service listens on.
        - `publicly_accessible (Optional[bool])`: Whether the service is publicly accessible. Defaults to True.
        - `min_instance_count (Optional[int])`: The minimum number of instances to keep running.
        - `max_instance_count (Optional[int])`: The maximum number of instances to run.
        - `max_instance_request_concurrency (Optional[int])`: The maximum number of requests each instance can handle concurrently.
        - `invokers (Optional[List[str]])`: A list of invokers that can access the service.
        - `custom_audiences (Optional[List[str]])`: A list of custom audiences that can access the service. See: [https://cloud.google.com/run/docs/configuring/custom-audiences](https://cloud.google.com/run/docs/configuring/custom-audiences)
        - `ingress (Optional[Literal])`: The ingress settings for the service. See: [https://cloud.google.com/run/docs/securing/ingress](https://cloud.google.com/run/docs/configuring/custom-audiences)
        - `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set for the service.
        """
        super().__init__(
            name=name,
            replacement_arguments={"region"},
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
        self.environment_variables = environment_variables

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        location = self.region or environment_state.gcp_config.default_region  # type: ignore
        return {
            "google_cloud_run_v2_service.service": f"projects/{environment_state.gcp_config.project_id}/locations/{location}/services/{self.resource_id}",  # type: ignore
        }

    def inputs(
        self, environment_state: EnvironmentState
    ) -> CloudRunServiceContainerInputs:
        return CloudRunServiceContainerInputs(
            resource_id=self.resource_id,
            region=self.region,
            cpu=self.cpu,
            memory=self.memory,
            port=self.port,
            publicly_accessible=self.publicly_accessible,
            min_instance_count=self.min_instance_count,
            max_instance_count=self.max_instance_count,
            max_instance_request_concurrency=self.max_instance_request_concurrency,
            invokers=self.invokers,
            custom_audiences=self.custom_audiences,
            ingress=self.ingress,
            launchflow_environment=lf.environment,
            launchflow_project=lf.project,
            environment_variables=self.environment_variables,
        )
