import dataclasses
from typing import Any, Dict, List, Literal, Optional

from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.gke_custom_domain_mapping import GKECustomDomainMapping
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.service import GCPDockerService
from launchflow.gcp.ssl import ManagedSSLCertificate
from launchflow.kubernetes.service import (
    ContainerResources,
    LivenessProbe,
    ReadinessProbe,
    ServiceContainer,
    StartupProbe,
    Toleration,
)
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DockerServiceOutputs


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    environment_variables: Optional[Dict[str, str]]


class GKEService(GCPDockerService):
    """A service hosted on a GKE Kubernetes Cluster.

    Like all [Services](/concepts/services), this class configures itself across multiple [Environments](/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/concepts/service).

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

    #### Deploy to GPU Enabled Node Pool
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster", delete_protection=False)
    node_pool = lf.gcp.NodePool(
        name="node-pool",
        cluster=cluster,
        machine_type="n1-standard-2",
        guest_accelerators=[lf.gcp.gke.GuestAccelerator(type="nvidia-tesla-t4", count=1)],
    )
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
    service = lf.gcp.GKEService(
        name="service",
        cluster=cluster,
        node_pool=node_pool,
        tolerations=[lf.kubernetes.service.Toleration(key="nvidia.com/gpu", value="present", operator="Equal")],
    )
    ```

    #### Service with a Horizontal Pod Autoscaler

    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService(
        "my-service",
        cluster=cluster,
        container_resources=lf.kubernetes.service.ContainerResources(
            requests=lf.kubernetes.service.ResourceQuantity(cpu="0.2"),
        ),
    )
    hpa = lf.kubernetes.HorizontalPodAutoscaler(
        "hpa",
        cluster=cluster,
        target_name=service.name
    )
    ```

    #### Service with a Custom Domain Mapping
    ```python
    import launchflow as lf

    cluster = lf.gcp.GKECluster("my-cluster")
    service = lf.gcp.GKEService(
        "my-service",
        cluster=cluster,
        domain="example.com"
        service_type="NodePort",
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
        container_resources: Optional[ContainerResources] = None,
        tolerations: Optional[List[Toleration]] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Create a new GKE Service.

        **Args:**
        - `name (str)`: The name of the service.
        - `cluster (GKECluster)`: The [GKE cluster](/reference/gcp-resources/gke#gke-cluster) to deploy the service to.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `node_pool (Optional[NodePool])`: The [node pool](/reference/gcp-resources/gke#node-pool) to deploy the service to.
        - `container_port (int)`: The port the service will listen on inside the container.
        - `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
        - `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
        - `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
        - `startup_probe (Optional[StartupProbe])`: The [startup probe](/reference/kubernetes-resources/service#startup-probe) for the service.
        - `liveness_probe (Optional[LivenessProbe])`: The [liveness probe](/reference/kubernetes-resources/service#liveness-probe) for the service.
        - `readiness_probe (Optional[ReadinessProbe])`: The [readiness probe](/reference/kubernetes-resources/service#readiness-probe) for the service.
        - `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set on the service container.
        - `container_resources (Optional[ContainerResources])`: The [container resources](/reference/kubernetes-resources/service#container-resources) for the service. NOTE: If you are creating a [HorizontalPodAutoscaler](/reference/kubernetes-resources/hpa) you will need to provide this.
        - `tolerations (Optional[List[Toleration]])`: A list of [tolerations](/reference/kubernetes-resources/service#toleration) for the service.
        - `domain (Optional[str])`: The domain to use for the service. `service_type` must be `NodePort` to assign a custom domain.
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
            container_resources=container_resources,
            tolerations=tolerations,
        )
        self.cluster = cluster
        self.namespace = namespace
        self.environment_variables = environment_variables
        self.domain = domain
        self._custom_domain_mapping = None
        self._ip_address = None
        self._ssl_certificate = None
        if domain:
            if service_type != "NodePort":
                raise ValueError(
                    "Custom domains are only supported for ClusterIP services. Please set service_type='ClusterIP' to use a custom domain."
                )
            self._ip_address = GlobalIPAddress(f"{name}-ip-address")
            self._ssl_certificate = ManagedSSLCertificate(
                f"{name}-ssl-certificate", domains=domain
            )
            self._custom_domain_mapping = GKECustomDomainMapping(
                f"{name}-domain-mapping",
                ip_address=self._ip_address,
                ssl_certificate=self._ssl_certificate,
                service_container=self.container,
            )
            self._custom_domain_mapping.resource_id = name

    def inputs(self, *args, **kwargs) -> GKEServiceInputs:
        # TODO: this should have a dependency on the resource but right now services can't depend on resources
        return GKEServiceInputs(self.environment_variables)

    def resources(self) -> List[Resource[Any]]:
        resources: List[Resource[Any]] = [self._artifact_registry, self.container]
        if self._custom_domain_mapping:
            resources.append(self._custom_domain_mapping)
        if self._ip_address:
            resources.append(self._ip_address)
        if self._ssl_certificate:
            resources.append(self._ssl_certificate)
        return resources

    def outputs(self) -> DockerServiceOutputs:
        repo_outputs = self._artifact_registry.outputs()
        if repo_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")
        container_outputs = self.container.outputs()
        ip_address = container_outputs.internal_ip
        if container_outputs.external_ip is not None:
            ip_address = container_outputs.external_ip
        dns_outputs = None
        if self._custom_domain_mapping:
            dns_outputs = self._custom_domain_mapping.dns_outputs()
        return DockerServiceOutputs(
            service_url=f"http://{ip_address}",
            docker_repository=repo_outputs.docker_repository,
            dns_outputs=dns_outputs,
        )
