import dataclasses
from typing import Any, List, Optional

from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.service import GCPService
from launchflow.kubernetes.service_container import ServiceContainer
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    pass


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
        container_port: int = 8080,
        target_port: int = 80,
        namespace: str = "default",
    ) -> None:
        super().__init__(name, dockerfile, build_directory, build_ignore)
        # TODO: I think we should leave this none cause k8s will let it run in any node pool
        # if you don't specify
        if node_pool is None:
            self.node_bool_managed = True
            self.node_pool = NodePool(f"{name}-node-pool", cluster=cluster)
        else:
            self.node_pool = node_pool
            self.node_pool_managed = False
        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER
        )
        self.container = ServiceContainer(
            name,
            cluster=cluster,
            namespace=namespace,
            node_pool=self.node_pool,
            container_port=container_port,
            host_port=target_port,
        )
        self.cluster = cluster
        self.namespace = namespace

    def inputs(self, *args, **kwargs) -> GKEServiceInputs:
        # TODO: this should have a dependency on the resource but right now services can't depend on resources
        return GKEServiceInputs()

    def resources(self) -> List[Resource[Any]]:
        resources = [self._artifact_registry, self.container]
        if self.node_pool_managed:
            resources.append(self.node_pool)
        return resources

    def outputs(self) -> ServiceOutputs:
        repo_outputs = self._artifact_registry.outputs()
        if repo_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")
        container_outputs = self.container.outputs()
        ip_address = container_outputs.internal_ip
        if container_outputs.external_ip is not None:
            ip_address = container_outputs.external_ip
        return ServiceOutputs(
            service_url=f"http://{ip_address}",
            docker_repository=repo_outputs.docker_repository,
            dns_outputs=None,
        )
