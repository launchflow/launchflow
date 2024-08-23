import dataclasses
from typing import Any, Dict, List, Literal, Optional

from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.service import GCPService
from launchflow.kubernetes.service_container import (
    LivenessProbe,
    ReadinessProbe,
    ServiceContainer,
    StartupProbe,
)
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    environment_variables: Optional[Dict[str, str]]


class GKEService(GCPService):
    product = ServiceProduct.GCP_GKE.value

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
        host_port: Optional[int] = None,
        namespace: str = "default",
        service_type: Literal["ClusterIP", "NodePort", "LoadBalancer"] = "LoadBalancer",
        startup_probe: Optional[StartupProbe] = None,
        liveness_probe: Optional[LivenessProbe] = None,
        readiness_probe: Optional[ReadinessProbe] = None,
        environment_variables: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name, dockerfile, build_directory, build_ignore)

        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER
        )
        self.container = ServiceContainer(
            name,
            cluster=cluster,
            namespace=namespace,
            node_pool=node_pool,
            container_port=container_port,
            host_port=host_port,
            startup_probe=startup_probe,
            liveness_probe=liveness_probe,
            readiness_probe=readiness_probe,
            service_type=service_type,
        )
        self.cluster = cluster
        self.namespace = namespace
        self.environment_variables = environment_variables

    def inputs(self, *args, **kwargs) -> GKEServiceInputs:
        # TODO: this should have a dependency on the resource but right now services can't depend on resources
        return GKEServiceInputs(self.environment_variables)

    def resources(self) -> List[Resource[Any]]:
        return [self._artifact_registry, self.container]

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
