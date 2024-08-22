import dataclasses
from typing import Literal, Optional
from typing_extensions import override

from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.kubernetes.resource import KubernetesResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class ServiceContainerInputs(ResourceInputs):
    cluster_id: str
    k8_provider: Literal["gke", "eks"]
    namespace: str
    node_pool_id: Optional[str]
    image: str
    container_port: int
    host_port: int


@dataclasses.dataclass
class ServiceContainerOutputs(Outputs):
    internal_ip: str
    external_ip: Optional[str]


class ServiceContainer(KubernetesResource[ServiceContainerOutputs]):
    product = ResourceProduct.KUBERNETES_SERVICE_CONTAINER

    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        *,
        namespace: str = "default",
        node_pool: Optional[NodePool] = None,
        image: str = "httpd",
        container_port: int = 80,
        host_port: int = 80,
    ):
        super().__init__(name, cluster)
        self.namespace = namespace
        self.node_pool = node_pool
        self.image = image
        self.container_port = container_port
        self.host_port = host_port

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
            k8_provider=k8_provider,
            namespace=self.namespace,
            node_pool_id=node_pool_id,
            image=self.image,
            container_port=self.container_port,
            host_port=self.host_port,
        )
