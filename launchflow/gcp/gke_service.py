import dataclasses
from typing import IO, TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple

from kubernetes import config as k8_config

from launchflow import exceptions
from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.gke import GKECluster, NodePool
from launchflow.gcp.gke_custom_domain_mapping import GKECustomDomainMapping
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.service import GCPService
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
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs
from launchflow.workflows.deploy_gcp_service import (
    build_artifact_registry_docker_image,
    promote_artifact_registry_docker_image,
)
from launchflow.workflows.k8s_service import update_k8s_service

if TYPE_CHECKING:
    from google.cloud.container import Cluster


def _get_gke_config(cluster_id: str, cluster: "Cluster") -> Dict[str, Any]:
    try:
        from google.auth import default
        from google.auth.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        raise exceptions.MissingGCPDependency()

    results: Tuple[Credentials, Any] = default()  # type: ignore
    credentials = results[0]
    if not credentials.valid:
        credentials.refresh(Request())
    return {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": cluster.master_auth.cluster_ca_certificate,
                    "server": f"https://{cluster.endpoint}",
                },
                "name": cluster_id,
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": cluster_id,
                    "user": "gke-user",
                },
                "name": f"{cluster_id}-context",
            }
        ],
        "current-context": f"{cluster_id}-context",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "gke-user",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": credentials.token,
                            "cmd-path": "gcloud",
                            "cmd-args": "config config-helper --format=json",
                            "expiry-key": "{.credential.token_expiry}",
                            "token-key": "{.credential.access_token}",
                        },
                    }
                },
            }
        ],
    }


@dataclasses.dataclass
class GKEServiceInputs(Inputs):
    environment_variables: Optional[Dict[str, str]]


@dataclasses.dataclass
class GKEServiceReleaseInputs:
    docker_image: str


class GKEService(GCPService[GKEServiceReleaseInputs]):
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
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args={
                "dockerfile": dockerfile,
            },
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
        self.dockerfile = dockerfile

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

    def outputs(self) -> ServiceOutputs:
        dns_outputs = None
        try:
            container_outputs = self.container.outputs()
            if self._custom_domain_mapping:
                dns_outputs = self._custom_domain_mapping.dns_outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        ip_address = container_outputs.internal_ip
        if container_outputs.external_ip is not None:
            ip_address = container_outputs.external_ip

        return ServiceOutputs(
            service_url=f"http://{ip_address}",
            dns_outputs=dns_outputs,
        )

    async def _build(
        self,
        *,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> GKEServiceReleaseInputs:
        artifact_registry_outputs = self._artifact_registry.outputs()

        # TODO: Make this field non-optional on the resource outputs
        if artifact_registry_outputs.docker_repository is None:
            raise RuntimeError("Docker repository not found")

        docker_image = await build_artifact_registry_docker_image(
            dockerfile_path=self.dockerfile,
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=build_log_file,
            artifact_registry_repository=artifact_registry_outputs.docker_repository,
            launchflow_project_name=launchflow_uri.project_name,
            launchflow_environment_name=launchflow_uri.environment_name,
            launchflow_service_name=self.name,
            launchflow_deployment_id=deployment_id,
            gcp_environment_config=gcp_environment_config,
            build_local=build_local,
        )

        return GKEServiceReleaseInputs(docker_image=docker_image)

    async def _promote(
        self,
        *,
        from_gcp_environment_config: GCPEnvironmentConfig,
        to_gcp_environment_config: GCPEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,
        promote_local: bool,
    ) -> GKEServiceReleaseInputs:
        from_artifact_registry_outputs = self._artifact_registry.outputs(
            project=from_launchflow_uri.project_name,
            environment=from_launchflow_uri.environment_name,
        )
        to_artifact_registry_outputs = self._artifact_registry.outputs(
            project=to_launchflow_uri.project_name,
            environment=to_launchflow_uri.environment_name,
        )
        if (
            from_artifact_registry_outputs.docker_repository is None
            or to_artifact_registry_outputs.docker_repository is None
        ):
            raise exceptions.ServiceOutputsMissingField(self.name, "docker_repository")

        docker_image = await promote_artifact_registry_docker_image(
            build_log_file=promote_log_file,
            from_artifact_registry_repository=from_artifact_registry_outputs.docker_repository,
            to_artifact_registry_repository=to_artifact_registry_outputs.docker_repository,
            launchflow_service_name=self.name,
            from_launchflow_deployment_id=from_deployment_id,
            to_launchflow_deployment_id=to_deployment_id,
            from_gcp_environment_config=from_gcp_environment_config,
            to_gcp_environment_config=to_gcp_environment_config,
            promote_local=promote_local,
        )

        return GKEServiceReleaseInputs(docker_image=docker_image)

    async def _release(
        self,
        *,
        release_inputs: GKEServiceReleaseInputs,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        try:
            from google.cloud import container_v1
        except ImportError:
            raise exceptions.MissingGCPDependency()
        location = None
        if self.cluster.regional:
            location = self.cluster.region or gcp_environment_config.default_region
        else:
            location = (
                self.cluster.zones[0]
                if self.cluster.zones
                else gcp_environment_config.default_zone
            )
        cluster_name = f"projects/{gcp_environment_config.project_id}/locations/{location}/clusters/{self.cluster.resource_id}"
        gcp_client = container_v1.ClusterManagerAsyncClient()
        cluster = await gcp_client.get_cluster(name=cluster_name)
        k8_config.load_kube_config_from_dict(_get_gke_config(cluster_name, cluster))

        await update_k8s_service(
            docker_image=release_inputs.docker_image,
            namespace=self.namespace,
            service_name=self.name,
            deployment_id=deployment_id,
            launchflow_environment=launchflow_uri.environment_name,
            launchflow_project=launchflow_uri.project_name,
            artifact_bucket=f"gs://{gcp_environment_config.artifact_bucket}",  # type: ignore
            cloud_provider="gcp",
            k8_service_account=gcp_environment_config.service_account_email.split("@")[0],  # type: ignore
            environment_vars=self.environment_variables,
        )
