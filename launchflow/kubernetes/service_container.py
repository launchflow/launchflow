import dataclasses
from typing import Literal, Optional

from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.kubernetes.resource import KubernetesResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class HTTPGet(Inputs):
    """An HTTPGet used by a Kubernetes probe.

    **Args:**
    - `path (str)`: The endpoint the probe should call.
    - `port (int)`: The port to probe.
    """

    path: str
    port: int


@dataclasses.dataclass
class StartupProbe(Inputs):
    """A StartupProbe used by a Kubernetes container.

    **Args:**
    - `http_get (HTTPGet)`: The HTTPGet probe to use.
    - `failure_threshold (int)`: The number of failures before the probe is considered failed.
    - `period_seconds (int)`: The number of seconds between probe checks.
    """

    http_get: HTTPGet
    failure_threshold: int
    period_seconds: int


@dataclasses.dataclass
class LivenessProbe(Inputs):
    """A LivenessProbe used by a Kubernetes container.

    **Args:**
    - `http_get (HTTPGet)`: The HTTPGet probe to use.
    - `initial_delay_seconds (int)`: The number of seconds to wait before starting probes.
    - `period_seconds (int)`: The number of seconds between probe checks.
    """

    http_get: HTTPGet
    initial_delay_seconds: int
    period_seconds: int


@dataclasses.dataclass
class ReadinessProbe(Inputs):
    """A LivenessProbe used by a Kubernetes container.

    **Args:**
    - `http_get (HTTPGet)`: The HTTPGet probe to use.
    - `initial_delay_seconds (int)`: The number of seconds to wait before starting probes.
    - `period_seconds (int)`: The number of seconds between probe checks.
    """

    http_get: HTTPGet
    initial_delay_seconds: int
    period_seconds: int


@dataclasses.dataclass
class ServiceContainerInputs(ResourceInputs):
    cluster_id: str
    k8_provider: Literal["gke", "eks"]
    namespace: str
    node_pool_id: Optional[str]
    image: str
    container_port: int
    host_port: Optional[int]
    startup_probe: Optional[StartupProbe]
    liveness_probe: Optional[LivenessProbe]
    readiness_probe: Optional[ReadinessProbe]
    service_type: Literal["ClusterIP", "NodePort", "LoadBalancer"]
    num_replicas: int


@dataclasses.dataclass
class ServiceContainerOutputs(Outputs):
    internal_ip: str
    external_ip: Optional[str] = None


class ServiceContainer(KubernetesResource[ServiceContainerOutputs]):
    """A container for a service running on a Kubernetes cluster.

    ### Example usage

    #### Basic Usage

    ```python
    import launchflow as lf

    cluster = lf.gke.GKECluster("my-cluster")
    container = lf.kubernetes.ServiceContainer("my-service")
    ```

    #### Custom Image

    ```python
    import launchflow as lf

    cluster = lf.gke.GKECluster("my-cluster")
    container = lf.kubernetes.ServiceContainer("my-service", image="nginx")
    ```
    """

    product = ResourceProduct.KUBERNETES_SERVICE_CONTAINER.value

    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        *,
        namespace: str = "default",
        num_replicas: int = 1,
        node_pool: Optional[NodePool] = None,
        image: str = "httpd",
        container_port: int = 80,
        host_port: Optional[int] = None,
        startup_probe: Optional[StartupProbe] = None,
        liveness_probe: Optional[LivenessProbe] = None,
        readiness_probe: Optional[ReadinessProbe] = None,
        service_type: Literal["ClusterIP", "NodePort", "LoadBalancer"] = "LoadBalancer",
    ):
        super().__init__(name, cluster)
        self.namespace = namespace
        self.node_pool = node_pool
        self.image = image
        self.container_port = container_port
        self.host_port = host_port
        self.startup_probe = startup_probe
        self.liveness_probe = liveness_probe
        self.readiness_probe = readiness_probe
        self.service_type = service_type
        self.num_replicas = num_replicas

    def inputs(self, environment_state: EnvironmentState) -> ServiceContainerInputs:
        cluster_id = None
        k8_provider = None
        if isinstance(self.cluster, GKECluster):
            cluster_id = Depends(self.cluster).gcp_id  # type: ignore
            k8_provider = "gke"
        else:
            raise NotImplementedError("Only GKE clusters are supported at this time.")
        node_pool_id = None
        if self.node_pool is not None:
            if isinstance(self.node_pool, NodePool):
                node_pool_id = Depends(self.node_pool).gcp_id  # type: ignore
            else:
                raise NotImplementedError(
                    "Only GKE node pools are supported at this time."
                )
        return ServiceContainerInputs(
            resource_id=self.resource_id,
            cluster_id=cluster_id,
            k8_provider=k8_provider,  # type: ignore
            namespace=self.namespace,
            node_pool_id=node_pool_id,
            image=self.image,
            container_port=self.container_port,
            host_port=self.host_port,
            startup_probe=self.startup_probe,
            liveness_probe=self.liveness_probe,
            readiness_probe=self.readiness_probe,
            service_type=self.service_type,  # type: ignore
            num_replicas=self.num_replicas,
        )
