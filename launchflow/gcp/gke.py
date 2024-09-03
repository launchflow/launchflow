import dataclasses
from typing import List, Literal, Optional, Union

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
    enable_tpu: Optional[bool]


class GKECluster(GCPResource[GKEOutputs]):
    """A Kubernetes Cluster hosted on GKE.

    NOTE: GKECluster is still in beta and is subject to change.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/kubernetes-engine).

    When a GKE cluster is created in an environment, LaunchFlow will connect the default namespace to the environment service account. This ensures that
    all service, workers, and jobs in the default namespace can access resources in the environment. If you would like to deploy and isolated service, worker, or
    job we recommend using a new namespace.

    ### Example Usage

    #### Create a GKE Cluster and Deploy a Service

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService("my-service", cluster=cluster)
    ```

    #### Create a Regional Cluster

    Force a regional cluster. By default LaunchFlow will use regional clusters for production environments and zonal clusters for development environments.

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster", regional=True, region="us-west1")
    ```

    #### Create a Single Zone Cluster

    Force a singl zone cluster. By default LaunchFlow will use regional clusters for production environments and zonal clusters for development environments.

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster", regional=False, zones="us-west1")
    ```

    #### Specify a Subnet

    If you create multiple clusters in your environment it is recommened you provide a custom IP range for the subnet for each cluster.

    ```python
    import launchflow as lf

    cluster1 = lf.gcp.GKECluster("my-cluster1", subnet_ip_cidr_range="10.90.0.0/20")
    cluster2 = lf.gcp.GKECluster("my-cluster2", subnet_ip_cidr_range="10.50.0.0/20")
    ```
    """

    product = ResourceProduct.GCP_GKE_CLUSTER.value

    def __init__(
        self,
        name: str,
        # TODO: we should add the option to have this auto discovered, currently you will have to change this
        # if you want to have multiple clusters in the same environment
        subnet_ip_cidr_range: str = "10.60.0.0/20",
        pod_ip_cidr_range: str = "192.168.0.0/18",
        service_cidr_range: str = "192.168.64.0/18",
        regional: Optional[bool] = None,
        region: Optional[str] = None,
        zones: Optional[Union[List[str], str]] = None,
        delete_protection: bool = False,
        enable_tpu: Optional[bool] = None,
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
        - `delete_protection (bool)`: Whether the cluster should have delete protection enabled.
        - `enable_tpu (bool)`: Whether the cluster should have TPU resources enabled. WARNING: This changing this will delete and recreate the cluster. Defaults to False. Defaults to False.
        """
        super().__init__(
            name,
            replacement_arguments={
                "subnet_ip_cidr_range",
                "pod_ip_cidr_range",
                "service_cidr_range",
                "regional",
                "region",
                "zones",
                "enable_tpu",
            },
        )
        self.subnet_ip_cidr_range = subnet_ip_cidr_range
        self.pod_ip_cidr_range = pod_ip_cidr_range
        self.service_cidr_range = service_cidr_range
        self.regional = regional
        self.region = region
        self.zones = None
        if zones is not None and not isinstance(zones, list):
            self.zones = [zones]
        else:
            self.zones = zones
        self.delete_protection = delete_protection
        self.enable_tpu = enable_tpu

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
            delete_protection=self.delete_protection,
            subnet_ip_cidr_range=self.subnet_ip_cidr_range,
            pod_ip_cidr_range=self.pod_ip_cidr_range,
            service_ip_cidr_range=self.service_cidr_range,
            regional=regional,
            region=region,
            zones=zones,
            enable_tpu=self.enable_tpu,
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
class GuestAccelerator(Inputs):
    type: str
    count: int


@dataclasses.dataclass
class NodePoolInputs(ResourceInputs):
    cluster_id: str
    machine_type: str
    preemptible: bool
    autoscaling: Optional[Autoscaling] = None
    disk_size_gb: Optional[int] = None
    disk_type: Optional[Literal["pd-standard", "pd-balanced", "pd-ssd"]] = None
    guest_accelerators: Optional[List[GuestAccelerator]] = None


class NodePool(GCPResource[NodePoolOutputs]):
    """A node pool for a GKE cluster.

    NOTE: This resource is currently in beta and may change in the future.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools).

    ### Example Usage

    #### Basic Example

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")
    ```

    #### Autoscaling Example

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    autoscaling = lf.gcp.gke.Autoscaling(min_node_count=1, max_node_count=10)
    node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro", autoscaling=autoscaling)
    ```

    #### Deploy Service to Node Pool

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")

    service = lf.gcp.GKEService("my-service", cluster=cluster, node_pool=node_pool)
    ```
    """

    product = ResourceProduct.GCP_GKE_NODE_POOL.value

    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        *,
        machine_type: str = "e2-medium",
        preemptible: bool = False,
        autoscaling: Optional[Autoscaling] = None,
        disk_size_gb: Optional[int] = None,
        disk_type: Optional[Literal["pd-standard", "pd-balanced", "pd-ssd"]] = None,
        guest_accelerators: Optional[List[GuestAccelerator]] = None,
    ):
        # TODO: add more customization options such as disk size, gpu support, etc..
        super().__init__(name)
        self.cluster = cluster
        self.autoscaling = autoscaling
        self.machine_type = machine_type
        self.preemptible = preemptible
        self.disk_size_gb = disk_size_gb
        self.disk_type = disk_type
        self.guest_accelerators = guest_accelerators

    def inputs(self, environment_state: EnvironmentState) -> NodePoolInputs:
        return NodePoolInputs(
            resource_id=self.resource_id,
            cluster_id=Depends(self.cluster).gcp_id,  # type: ignore
            autoscaling=self.autoscaling,
            machine_type=self.machine_type,
            preemptible=self.preemptible,
            disk_size_gb=self.disk_size_gb,
            disk_type=self.disk_type,  # type: ignore
            guest_accelerators=self.guest_accelerators,
        )
