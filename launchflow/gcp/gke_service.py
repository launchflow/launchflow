import dataclasses
from typing import Any, Dict, List, Literal, Optional

from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.service import GCPDockerService
from launchflow.kubernetes.service_container import (
    LivenessProbe,
    ReadinessProbe,
    ServiceContainer,
    StartupProbe,
)
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DockerServiceOutputs, ServiceOutputs


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    environment_variables: Optional[Dict[str, str]]


class GKEService(GCPDockerService):
    """A service hosted on a GKE Kubernetes Cluster.

    Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/service).

    ### Example Usage

    #### Basic Usage
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService("my-service", cluster=cluster)
    ```

    #### Custom Dockerfile Path
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService(
        "my-service",
        cluster=cluster,
        dockerfile="docker/Dockerfile"m
        build_directory="path/to/service_dir",
    )
    ```

    #### Use a Custom Node Pool
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")

    service = lf.gcp.GKEService("my-service", cluster=cluster, node_pool=node_pool)
    ```

    #### Service with a Startup Probe
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService(
        "my-service",
        cluster=cluster,
        startup_probe=lf.kubernetes.StartupProbe(
            path="/healthz",
            initial_delay_seconds=5,
            period_seconds=10,
        ),
    )
    ```
    """

    product = ServiceProduct.GCP_GKE.value

    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        *,
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
        # TODO: add support for custom domains
    ) -> None:
        """Create a new GKE Service.

        **Args:**
        - `name (str)`: The name of the service.
        - `cluster ([GKECluster](/docs/reference/gcp-resources/gke#gke-cluster))`: The GKE cluster to deploy the service to.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `node_pool ([NodePool](/docs/reference/gcp-resources/gke#node-pool))`: The node pool to deploy the service to. If not provided, the default node pool will be used.
        - `container_port (int)`: The port the service will listen on inside the container.
        - `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
        - `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
        - `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
        - `startup_probe ([StartupProbe](/docs/reference/kubernetes-resources/service-container#startup-probe))`: The startup probe for the service.
        - `liveness_probe ([LivenessProbe](/docs/reference/kubernetes-resources/service-container#liveness-probe))`: The liveness probe for the service.
        - `readiness_probe ([ReadinessProbe](/docs/reference/kubernetes-resources/service-container#readiness-probe))`: The readiness probe for the service.
        - `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set on the service container.
        """
        super().__init__(
            name=name,
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )

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

    def outputs(self) -> DockerServiceOutputs:
        repo_outputs = self._artifact_registry.outputs()
        if repo_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")
        container_outputs = self.container.outputs()
        ip_address = container_outputs.internal_ip
        if container_outputs.external_ip is not None:
            ip_address = container_outputs.external_ip
        return DockerServiceOutputs(
            service_url=f"http://{ip_address}",
            docker_repository=repo_outputs.docker_repository,
            dns_outputs=None,
        )
