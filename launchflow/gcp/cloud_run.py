from dataclasses import dataclass
from typing import IO, Dict, List, Literal, Optional

from launchflow import exceptions
from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.cloud_run_container import CloudRunServiceContainer
from launchflow.gcp.custom_domain_mapping import CustomDomainMapping
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.service import GCPService
from launchflow.gcp.ssl import ManagedSSLCertificate
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


async def _release_cloud_run(
    cloud_run_id: str,
    docker_image: str,
    gcp_environment_config: GCPEnvironmentConfig,
    launchflow_uri: LaunchFlowURI,
    deployment_id: str,
):
    try:
        from google.cloud import run_v2
    except ImportError:
        raise exceptions.MissingGCPDependency()

    client = run_v2.ServicesAsyncClient()
    service = await client.get_service(name=cloud_run_id)
    # Updating the service container will trigger a new revision to be created
    service.template.containers[0].image = docker_image

    # Add or update the environment variables
    fields_to_add = {
        "LAUNCHFLOW_ARTIFACT_BUCKET": f"gs://{gcp_environment_config.artifact_bucket}",
        "LAUNCHFLOW_PROJECT": launchflow_uri.project_name,
        "LAUNCHFLOW_ENVIRONMENT": launchflow_uri.environment_name,
        "LAUNCHFLOW_CLOUD_PROVIDER": "gcp",
        "LAUNCHFLOW_DEPLOYMENT_ID": deployment_id,
    }
    for env_var in service.template.containers[0].env:
        if env_var.name in fields_to_add:
            env_var.value = fields_to_add[env_var.name]
            del fields_to_add[env_var.name]
    for key, value in fields_to_add.items():
        service.template.containers[0].env.append(run_v2.EnvVar(name=key, value=value))

    operation = await client.update_service(request=None, service=service)
    await operation.result()


@dataclass
class CloudRunInputs(Inputs):
    pass


@dataclass
class CloudRunServiceReleaseInputs:
    docker_image: str


class CloudRunService(GCPService[CloudRunServiceReleaseInputs]):
    """A service hosted on GCP Cloud Run.

    ### Example Usage

    #### Basic Usage
    ```python
    import launchflow as lf

    service = lf.gcp.CloudRunService("my-service", cpu=4)
    ```

    #### Custom Environment Variables
    ```python
    import launchflow as lf

    service = lf.gcp.CloudRunService(
        "my-service",
        environment_variables={"MY_ENV_VAR": "my-value"}
    )
    ```

    **NOTE:** This will create the following infrastructure in your GCP project:
    - A [Cloud Run](https://cloud.google.com/run) service with the specified configuration.
    - A [Load Balancer](https://cloud.google.com/load-balancing) to route traffic to the service.
    - A [Cloud Build](https://cloud.google.com/build) trigger that builds and deploys the service.
    - An [Artifact Registry](https://cloud.google.com/artifact-registry) repository to store the service's Docker image.
    """

    product = ServiceProduct.GCP_CLOUD_RUN.value

    def __init__(
        self,
        name: str,
        # build inputs
        build_directory: str = ".",
        build_ignore: List[str] = [],
        dockerfile: str = "Dockerfile",
        # cloud run inputs
        region: Optional[str] = None,
        cpu: Optional[int] = None,
        memory: Optional[str] = None,
        port: Optional[int] = None,
        # TODO: don't think this needs to be optional, and the docstring says it defaults to true, which is only true if the default is in cloud run or somewhere downstream in our code
        publicly_accessible: Optional[bool] = None,
        min_instance_count: Optional[int] = None,
        max_instance_count: Optional[int] = None,
        max_instance_request_concurrency: Optional[int] = None,
        invokers: Optional[List[str]] = None,
        custom_audiences: Optional[List[str]] = None,
        ingress: Optional[
            Literal[
                "INGRESS_TRAFFIC_ALL",
                "INGRESS_TRAFFIC_INTERNAL_ONLY",
                "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
            ]
        ] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        # custom domain inputs
        domain: Optional[str] = None,
    ) -> None:
        """Creates a new Cloud Run service.

        **Args:**
        - `name (str)`: The name of the service.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `region (Optional[str])`: The region to deploy the service to.
        - `cpu (Optional[int])`: The number of CPUs to allocate to each instance of the service.
        - `memory (Optional[str])`: The amount of memory to allocate to each instance of the service.
        - `port (Optional[int])`: The port the service listens on.
        - `publicly_accessible (Optional[bool])`: Whether the service is publicly accessible. Defaults to True.
        - `min_instance_count (Optional[int])`: The minimum number of instances to keep running.
        - `max_instance_count (Optional[int])`: The maximum number of instances to run.
        - `max_instance_request_concurrency (Optional[int])`: The maximum number of requests each instance can handle concurrently.
        - `invokers (Optional[List[str]])`: A list of invokers that can access the service.
        - `custom_audiences (Optional[List[str]])`: A list of custom audiences that can access the service. See: [https://cloud.google.com/run/docs/configuring/custom-audiences](https://cloud.google.com/run/docs/configuring/custom-audiences).
        - `ingress (Optional[Literal["INGRESS_TRAFFIC_ALL", "INGRESS_TRAFFIC_INTERNAL_ONLY", "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"]])`: The ingress settings for the service. See: [https://cloud.google.com/run/docs/securing/ingress](https://cloud.google.com/run/docs/configuring/custom-audiences).
        - `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set for the service.
        - `domain (Optional[str])`: The custom domain to map to the service.
        """
        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args={
                "dockerfile": dockerfile,
            },
        )
        self.region = region
        self.cpu = cpu
        self.memory = memory
        self.port = port
        self.publicly_accessible = publicly_accessible
        self.min_instance_count = min_instance_count
        self.max_instance_count = max_instance_count
        self.max_instance_request_concurrency = max_instance_request_concurrency
        self.invokers = invokers
        self.custom_audiences = custom_audiences
        self.ingress = ingress
        self.dockerfile = dockerfile

        # Resources - flows should not access these directly
        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER, location=region
        )
        self._artifact_registry.resource_id = name
        self._cloud_run_service_container = CloudRunServiceContainer(
            f"{name}-container",
            region=region,
            cpu=cpu,
            memory=memory,
            port=port,
            publicly_accessible=publicly_accessible,
            min_instance_count=min_instance_count,
            max_instance_count=max_instance_count,
            max_instance_request_concurrency=max_instance_request_concurrency,
            invokers=invokers,
            custom_audiences=custom_audiences,
            ingress=ingress,
            environment_variables=environment_variables,
        )
        self._cloud_run_service_container.resource_id = name

        self._custom_domain_mapping: Optional[CustomDomainMapping] = None
        self._ip_address: Optional[GlobalIPAddress] = None
        self._ssl_certificate: Optional[ManagedSSLCertificate] = None

        if domain:
            self._ip_address = GlobalIPAddress(f"{name}-ip-address")
            self._ssl_certificate = ManagedSSLCertificate(
                f"{name}-ssl-certificate", domains=domain
            )
            self._custom_domain_mapping = CustomDomainMapping(
                f"{name}-domain-mapping",
                ip_address=self._ip_address,
                ssl_certificate=self._ssl_certificate,
                cloud_run=self._cloud_run_service_container,
            )
            self._custom_domain_mapping.resource_id = name

    def inputs(self) -> CloudRunInputs:
        return CloudRunInputs()

    def resources(self) -> List[Resource]:
        to_return: List[Resource] = [
            self._artifact_registry,
            self._cloud_run_service_container,
        ]
        if self._ip_address is not None:
            to_return.append(self._ip_address)
        if self._ssl_certificate is not None:
            to_return.append(self._ssl_certificate)
        if self._custom_domain_mapping is not None:
            to_return.append(self._custom_domain_mapping)
        return to_return

    def outputs(self) -> ServiceOutputs:
        dns_outputs = None
        try:
            service_container_outputs = self._cloud_run_service_container.outputs()
            if self._custom_domain_mapping:
                dns_outputs = self._custom_domain_mapping.dns_outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_outputs = ServiceOutputs(
            service_url=service_container_outputs.service_url,
            dns_outputs=dns_outputs,
        )
        service_outputs.gcp_id = service_container_outputs.gcp_id

        return service_outputs

    async def _build(
        self,
        *,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> CloudRunServiceReleaseInputs:
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

        return CloudRunServiceReleaseInputs(docker_image=docker_image)

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
    ) -> CloudRunServiceReleaseInputs:
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

        return CloudRunServiceReleaseInputs(docker_image=docker_image)

    async def _release(
        self,
        *,
        release_inputs: CloudRunServiceReleaseInputs,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        cloud_run_outputs = self._cloud_run_service_container.outputs()
        if cloud_run_outputs.gcp_id is None:
            raise exceptions.ServiceOutputsMissingField(self.name, "gcp_id")

        await _release_cloud_run(
            cloud_run_id=cloud_run_outputs.gcp_id,
            docker_image=release_inputs.docker_image,
            gcp_environment_config=gcp_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
        )
