import dataclasses
from typing import Dict, List, Literal, Optional

from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.kubernetes.resource import KubernetesResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class Toleration:
    """A Kubernetes toleration applied to a service.

    **Args:**
    - `key (str)`: The key to match against.
    - `value (str)`: The value to match against.
    - `operator (Literal["Equal", "Exists"])`: The operator to use.
    - `effect (Optional[str])`: The effect to apply.
    """

    key: str = ""
    value: str = ""
    operator: Literal["Equal", "Exists"] = "Equal"
    effect: Optional[str] = None


@dataclasses.dataclass
class ResourceQuantity(Inputs):
    """Resource information for a Kubernetes container.

    **Args:**
    - `cpu (str)`: The CPU limit or request.
    - `memory (str)`: The memory limit or request.
    """

    cpu: Optional[str] = None
    memory: Optional[str] = None


@dataclasses.dataclass
class ContainerResources(Inputs):
    """ContainerResources used by a Kubernetes container.

    **Args:**
    - `limit (ContainerResourceInputs)`: The resource limits for the container.
    - `request (ContainerResourceInputs)`: The resource requests for the container.
    """

    limits: Optional[ResourceQuantity] = None
    requests: Optional[ResourceQuantity] = None


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
    container_resources: Optional[ContainerResources]
    tolerations: Optional[List[Toleration]]
    annotations: Optional[Dict[str, str]]


@dataclasses.dataclass
class ServiceContainerOutputs(Outputs):
    internal_ip: str
    external_ip: Optional[str] = None


class ServiceContainer(KubernetesResource[ServiceContainerOutputs]):
    """A container for a service running on a Kubernetes cluster.

    NOTE: ServiceContainer is still in beta and is subject to change.

    This will create a deployment and a service containing that deployment on the Kubernetes cluster.

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
        container_resources: Optional[ContainerResources] = None,
        tolerations: Optional[List[Toleration]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ):
        """Create a new ServiceContainer.

        **Args:**
        - `name (str)`: The name of the service.
        - `cluster (GKECluster)`: The [GKE cluster](/docs/reference/gcp-resources/gke#gke-cluster) to deploy the service to.
        - `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
        - `num_replicas`: The number of replicas to start.
        - `node_pool (Optional[NodePool])`: The [node pool](/docs/reference/gcp-resources/gke#node-pool) to deploy the service to.
        - `image (str)`: The Docker image to user for the deployment. Defaults to `httpd`.
        - `container_port (int)`: The port the service will listen on inside the container.
        - `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
        - `startup_probe (Optional[StartupProbe])`: The [startup probe](#startup-probe) for the service.
        - `liveness_probe (Optional[LivenessProbe])`: The [liveness probe](#liveness-probe) for the service.
        - `readiness_probe (Optional[ReadinessProbe])`: The [readiness probe](#readiness-probe) for the service.
        - `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
        - `container_resources (Optional[ContainerResources])`: The [container resources](#container-resources) for the service. NOTE: If you are creating a [HorizontalPodAutoscaler](/docs/reference/kubernetes-resources/horizonal-pod-autoscaler) you will need to provide this.
        - `tolerations (Optional[List[Toleration]])`: A list of [tolerations](#tolerations) for the service.
        - `annotations (Optional[Dict[str, str]])`: A dictionary of annotations to add to the service.
        """
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
        self.container_resources = container_resources
        self.toleration = tolerations
        self.annotations = annotations

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
            container_resources=self.container_resources,
            tolerations=self.toleration,
            annotations=self.annotations,
        )
