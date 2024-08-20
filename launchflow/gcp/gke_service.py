import dataclasses
from typing import Any, List, Optional

from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.service import GCPService
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    cluster_name: str
    port: int
    namespace: str


class GKEService(GCPService):
    product = ServiceProduct.GCP_GKE

    def __init__(
        self,
        name: str,
        *,
        cluster: GKECluster,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],
        node_pool: Optional[NodePool] = None,
        port: int = 80,
        namespace: str = "default",
    ) -> None:
        super().__init__(name, dockerfile, build_directory, build_ignore)
        if node_pool is None:
            self.node_pool = NodePool(f"{name}-node-pool", cluster=cluster)
        else:
            self.node_pool = node_pool
        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER
        )
        self.cluster = cluster
        self.port = port
        self.namespace = namespace

    def inputs(self, *args, **kwargs) -> GKEServiceInputs:
        # TODO: this should have a dependency on the resource but right now services can't depend on resources
        return GKEServiceInputs(
            cluster_name=self.cluster.name,
            port=self.port,
            namespace=self.namespace,
        )

    def resources(self) -> List[Resource[Any]]:
        return [self.node_pool, self._artifact_registry, self.cluster]

    def outputs(self) -> ServiceOutputs:
        repo_outputs = self._artifact_registry.outputs()
        if repo_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")
        return ServiceOutputs(
            service_url="",  # TODO: make this a real URL
            docker_repository=repo_outputs.docker_repository,
            dns_outputs=None,
        )
