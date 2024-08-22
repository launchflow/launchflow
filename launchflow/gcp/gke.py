import dataclasses
from typing import List, Literal, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import EnvironmentType, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class GKEOutputs(Outputs):
    pass


@dataclasses.dataclass
class GKEInputs(ResourceInputs):
    subnet_ip_cidr_range: str
    pod_ip_cidr_range: str
    service_ip_cidr_range: str
    delete_protection: bool
    regional: bool
    region: Optional[str]
    zones: Optional[List[str]]


class GKECluster(GCPResource[GKEOutputs]):
    product = ResourceProduct.GCP_GKE_CLUSTER

    def __init__(
        self,
        name: str,
        subnet_ip_cidr_range: str = "10.60.0.0/20",
        pod_ip_cidr_range: str = "192.168.0.0/18",
        service_cidr_range: str = "192.168.64.0/18",
        regional: Optional[bool] = None,
        region: Optional[str] = None,
        zones: Optional[List[str]] = None,
    ):
        """Creates a new GKE Cluster.

        **Args:**
        - `name (str)`: The name of the GKE cluster.
        - `subnet_ip_cidr_range (str)`: The IP range for the cluster's subnet.
        - `pod_ip_cidr_range (str)`: The IP range for the cluster's pods.
        - `service_cidr_range (str)`: The IP range for the cluster's services.
        - `regional (Optional[bool])`: Whether the cluster is regional or zonal. If not provided will default to True for production environments and False for development environments.
        - `region (Optional[str])`: The region for the cluster. If not provided will default to the default region for the environment.
        - `zones (Optional[List[str]])`: The zones for the cluster. If not provided will default to the default zone for development environments, and remain unset for production environments.
        """
        super().__init__(name)
        self.subnet_ip_cidr_range = subnet_ip_cidr_range
        self.pod_ip_cidr_range = pod_ip_cidr_range
        self.service_cidr_range = service_cidr_range
        self.regional = regional
        self.region = region
        self.zones = zones

    def inputs(self, environment_state: EnvironmentState) -> GKEInputs:
        zones = self.zones
        region = self.region or environment_state.gcp_config.default_region  # type: ignore
        regional = self.regional
        if not regional:
            if environment_state.environment_type == EnvironmentType.DEVELOPMENT:
                regional = False
            else:
                regional = True
        if not regional:
            if not zones:
                zones = [environment_state.gcp_config.default_zone]  # type: ignore
        return GKEInputs(
            resource_id=self.resource_id,
            delete_protection=False,
            subnet_ip_cidr_range=self.subnet_ip_cidr_range,
            pod_ip_cidr_range=self.pod_ip_cidr_range,
            service_ip_cidr_range=self.service_cidr_range,
            regional=regional,
            region=region,
            zones=zones,
        )


@dataclasses.dataclass
class NodePoolOutputs(Outputs):
    pass


@dataclasses.dataclass
class Autoscaling(Inputs):
    """Autoscaling configurate for a GKE Node Pool.

    **Args:***
    - `min_node_count (int)`: The minimum number of nodes per zone in the node pool. Cannot be used with the `total_*` limits.
    - `max_node_count (int)`: The maximum number of nodes per zone in the node pool. Cannot be used with the `total_*` limits.
    - `total_min_node_count (int)`: The minimum number of nodes in the node pool. Cannot be used with the zone limits.
    - `total_max_node_count (int)`: The maximum number of nodes in the node pool. Cannot be used with the zone limits.
    """

    min_node_count: Optional[int] = None
    max_node_count: Optional[int] = None
    total_min_node_count: Optional[int] = None
    total_max_node_count: Optional[int] = None
    location_policy: Optional[Literal["BALANCED", "ANY"]] = None


@dataclasses.dataclass
class NodePoolInputs(ResourceInputs):
    cluster_id: str
    machine_type: str
    preemptible: bool
    autoscaling: Optional[Autoscaling] = None


class NodePool(GCPResource[NodePoolOutputs]):
    product = ResourceProduct.GCP_GKE_NODE_POOL

    def __init__(
        self,
        name: str,
        *,
        cluster: GKECluster,
        machine_type: str = "e2-medium",
        preemptible: bool = False,
        autoscaling: Optional[Autoscaling] = None,
    ):
        super().__init__(name)
        self.cluster = cluster
        self.autoscaling = autoscaling
        self.machine_type = machine_type
        self.preemptible = preemptible

    def inputs(self, environment_state: EnvironmentState) -> NodePoolInputs:
        return NodePoolInputs(
            resource_id=self.resource_id,
            cluster_id=Depends(self.cluster).gcp_id,  # type: ignore
            autoscaling=self.autoscaling,
            machine_type=self.machine_type,
            preemptible=self.preemptible,
        )
