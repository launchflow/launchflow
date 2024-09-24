import asyncio
import dataclasses
import json
import time
from datetime import timedelta
from typing import IO, Any, Callable, List, Literal, Optional, Union

from launchflow import exceptions
from launchflow.gcp.artifact_registry_repository import (
    ArtifactRegistryRepository,
    RegistryFormat,
)
from launchflow.gcp.custom_domain_mapping import CustomDomainMapping, GCEServiceBackend
from launchflow.gcp.global_ip_address import GlobalIPAddress
from launchflow.gcp.http_health_check import HttpHealthCheck
from launchflow.gcp.networking import AllowRule, FirewallAllowRule
from launchflow.gcp.regional_autoscaler import (
    AutoscalingPolicy,
    CPUUtilization,
    RegionalAutoscaler,
)
from launchflow.gcp.regional_managed_instance_group import (
    AutoHealingPolicy,
    NamedPort,
    RegionalManagedInstanceGroup,
    UpdatePolicy,
)
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


async def _wait_for_op(op):
    while not op.done():
        await asyncio.sleep(2)
    return op.result()


_DISCONNECTED_RETRIES = 5


async def _retry_remote_disconnected(fn: Callable, *args, **kwargs):
    loop = asyncio.get_event_loop()
    tries = _DISCONNECTED_RETRIES
    while tries > 0:
        try:
            return await loop.run_in_executor(None, fn, *args, **kwargs)
        except ConnectionError:
            tries -= 1
            if tries == 0:
                raise
            await asyncio.sleep(2)
    raise ValueError("Failed to connect to remote service")


async def _poll_mig_updating(
    client: Any, mig_name: str, project: str, region: str, timeout: timedelta
):
    def get_mig():
        return client.get(
            project=project, region=region, instance_group_manager=mig_name
        )

    mig = await _retry_remote_disconnected(get_mig)
    start_time = time.time()
    while not mig.status.is_stable:
        now = time.time()
        if now - start_time > timeout.total_seconds():
            raise exceptions.GCEServiceNotHealthyTimeout(timeout)
        await asyncio.sleep(2)
        mig = await _retry_remote_disconnected(get_mig)


async def _release_compute_engine_service(
    *,
    docker_image: str,
    machine_type: str,
    disk_size_gb: int,
    deploy_timeout: timedelta,
    gcp_environment_config: GCPEnvironmentConfig,
    launchflow_uri: LaunchFlowURI,
    deployment_id: str,
    service_name: str,
    mig_resource_id: str,
    region: str,
):
    try:
        from google.cloud import compute
    except ImportError:
        raise exceptions.MissingGCPDependency()

    template_client = compute.InstanceTemplatesClient()
    template = compute.InstanceTemplate(
        name=f"{service_name}-{deployment_id}",
        properties=compute.InstanceProperties(
            machine_type=machine_type,
            disks=[
                compute.AttachedDisk(
                    boot=True,
                    auto_delete=True,
                    initialize_params=compute.AttachedDiskInitializeParams(
                        disk_size_gb=disk_size_gb,
                        source_image="https://www.googleapis.com/compute/v1/projects/cos-cloud/global/images/cos-stable-109-17800-147-54",
                    ),
                ),
            ],
            tags=compute.Tags(items=[mig_resource_id]),
            labels={"container-vm": "cos-stable-109-17800-147-54"},
            metadata=compute.Metadata(
                items=[
                    compute.Items(
                        key="google-logging-enabled",
                        value="true",
                    ),
                    compute.Items(
                        key="google-monitoring-enabled",
                        value="true",
                    ),
                    compute.Items(
                        key="gce-container-declaration",
                        value=json.dumps(
                            {
                                "spec": {
                                    "containers": [
                                        {
                                            "image": docker_image,
                                            "env": [
                                                {
                                                    "name": "LAUNCHFLOW_ARTIFACT_BUCKET",
                                                    "value": f"gs://{gcp_environment_config.artifact_bucket}",
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_PROJECT",
                                                    "value": launchflow_uri.project_name,
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_ENVIRONMENT",
                                                    "value": launchflow_uri.environment_name,
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_CLOUD_PROVIDER",
                                                    "value": "gcp",
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_DEPLOYMENT_ID",
                                                    "value": deployment_id,
                                                },
                                            ],
                                        },
                                    ]
                                },
                                "volumes": [],
                                "restartPolicy": "Always",
                            }
                        ),
                    ),
                ]
            ),
            network_interfaces=[
                compute.NetworkInterface(
                    network=f"https://www.googleapis.com/compute/beta/projects/{gcp_environment_config.project_id}/global/networks/default",
                    access_configs=[
                        compute.AccessConfig(
                            name="External NAT",
                            type="ONE_TO_ONE_NAT",
                        ),
                    ],
                )
            ],
            service_accounts=[
                compute.ServiceAccount(
                    email=gcp_environment_config.service_account_email,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            ],
        ),
    )

    def insert_template():
        return template_client.insert(
            project=gcp_environment_config.project_id,
            instance_template_resource=template,
        )

    template_op = await _retry_remote_disconnected(insert_template)

    await _wait_for_op(template_op)

    group_client = compute.RegionInstanceGroupManagersClient()

    def update_instances():
        return group_client.patch(
            instance_group_manager=mig_resource_id,
            project=gcp_environment_config.project_id,
            region=region,
            instance_group_manager_resource=compute.InstanceGroupManager(
                versions=[
                    compute.InstanceGroupManagerVersion(
                        instance_template=f"projects/{gcp_environment_config.project_id}/global/instanceTemplates/{template.name}",
                        name=template.name,
                    )
                ],
                update_policy=compute.InstanceGroupManagerUpdatePolicy(
                    type_="PROACTIVE"
                ),
            ),
        )

    update_op = await _retry_remote_disconnected(update_instances)
    await _wait_for_op(update_op)
    await _poll_mig_updating(
        group_client,
        mig_resource_id,
        gcp_environment_config.project_id,  # type: ignore
        region,
        deploy_timeout,
    )


@dataclasses.dataclass
class ComputeEngineServiceInputs(Inputs):
    machine_type: str
    disk_size_gb: int
    deploy_timeout_sec: float


@dataclasses.dataclass
class ComputeEngineServiceReleaseInputs:
    docker_image: str


class ComputeEngineService(GCPService[ComputeEngineServiceReleaseInputs]):
    """A service hosted on a managed instance group on GCP Compute Engine.

    Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/products/compute?hl=en#virtual-machines-for-any-workload).

    ### Example Usage

    #### Basic Usage

    ```python
    import launchflow as lf

    service = lf.gcp.ComputeEngineService("my-service")
    ```

    #### Custom Docker Image / Build Configuration

    ```python
    import launchflow as lf

    service = lf.gcp.ComputeEngineService(
        "my-service",
        build_directory="my-service",
        dockerfile="docker/Dockerfile",
        build_ignore=["secrets"]
    )
    ```

    #### Custom Machine Type

    ```python
    import launchflow as lf

    service = lf.gcp.ComputeEngineService("my-serfice", machine_type="n1-standard-4")
    ```

    #### Custom Health Check

    ```python
    import launchflow as lf

    health_check = lf.gcp.HttpHealthCheck("my-health-check", port=80, request_path="/health")
    service = lf.gcp.ComputeEngineService("my-service", health_check=health_check)
    ```
    """

    product = ServiceProduct.GCP_COMPUTE_ENGINE.value

    def __init__(
        self,
        name: str,
        # build inputs
        build_directory: str = ".",
        build_ignore: List[str] = [],
        dockerfile: str = "Dockerfile",
        # gce inputs
        machine_type: str = "e2-standard-2",
        port: int = 80,
        region: Optional[str] = None,
        disk_size_gb: int = 10,
        update_policy: UpdatePolicy = UpdatePolicy(max_surge_fixed=3),
        # health check inputs
        health_check: Optional[Union[Literal[False], HttpHealthCheck]] = None,
        auto_healing_policy_initial_delay: int = 360,
        # autoscaler
        autoscaler: Optional[Union[Literal[False], RegionalAutoscaler]] = None,
        # custom domain
        domain: Optional[str] = None,
        # deploy configuraiton
        deploy_timeout: timedelta = timedelta(minutes=15),
    ):
        """Create a new Compute Engine Service.

        **Args:**
        - `name (str)`: The name of the service.
        - `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
        - `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
        - `machine_type (str)`: The machine type to use for the service. This should be one of the [supported machine types](https://cloud.google.com/compute/docs/machine-types). Defualts to `e2-standard-2`.
        - `port (int)`: The port the service will listen on. Defaults to 80.
        - `region (str)`: The region to deploy the service to. If not provided, the service will be deployed to the default region for the environment.
        - `disk_size_gb (int)`: The size of the disk in GB. Defaults to 10.
        - `update_policy (UpdatePolicy)`: The [update policy](/reference/gcp-resources/regional-managed-instance-group#update-policy) for the managed instance group. Defaults to `UpdatePolicy(max_surge_fixed=3)`.
        - `health_check (Optional[Union[Literal[False], HttpHealthCheck]])`: The [health check](/reference/gcp-resources/http-health-check) to use for the service. If `False`, no health check will be used. If `None`, a default health check will be created that performs a health check on the `/` endpoint every 5 seconds. Defaults to `None`.
        - `auto_healing_policy_initial_delay (int)`: The initial delay in seconds for the [auto healing policy](/reference/gcp-resources/regional-managed-instance-group#auto-healing-policy). Defaults to 360.
        - `autoscaler (Optional[Union[Literal[False], RegionalAutoscaler]])`: The [autoscaler](/reference/gcp-resources/regional-autoscaler) to use for the service. If `False`, no autoscaler will be used. If `None` a default autoscaler will be used that scales between 1-10 VMs with a target CPU utilization of .75. Defaults to `None`.
        - `domain (Optional[str])`: The custom domain to use for the service. If not provided no load balancer will be setup in front of the managed instance group.
        - `deploy_timeout (timedelta)`: The amount of time to wait for the service to deploy before timing out. Defaults to 15 minutes.
        """
        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args={
                "dockerfile": dockerfile,
            },
        )
        self.machine_type = machine_type
        self.port = port
        self.region = region
        self.disk_size_gb = disk_size_gb
        self.dockerfile = dockerfile

        auto_healing_policy = None
        if health_check is False:
            self._health_check = None
        elif health_check is None:
            self._health_check = HttpHealthCheck(f"{name}-health-check", port=port)
            auto_healing_policy = AutoHealingPolicy(
                health_check=self._health_check, initial_delay_sec=180
            )
        else:
            self._health_check = health_check
            auto_healing_policy = AutoHealingPolicy(
                health_check=self._health_check, initial_delay_sec=180
            )

        self._mig = RegionalManagedInstanceGroup(
            name,
            region=region,
            auto_healing_policy=auto_healing_policy,
            update_policy=update_policy,
            named_ports=[NamedPort("http", port)],
        )

        if autoscaler is False:
            self._health_check = None
        elif autoscaler is None:
            self._autoscaler = RegionalAutoscaler(
                f"{name}-auto-scaler",
                group_manager=self._mig,
                autoscaling_policies=[
                    AutoscalingPolicy(
                        min_replicas=1,
                        max_replicas=10,
                        cooldown_period=360,
                        cpu_utilization=CPUUtilization(target=0.75),
                    )
                ],
            )
        else:
            self._autoscaler = autoscaler
        self._firewall_rule = FirewallAllowRule(
            name=f"{self.name}-allow",
            direction="INGRESS",
            allow_rules=[AllowRule(ports=[port], protocol="tcp")],
            target_tags=[self.name],
            source_ranges=["0.0.0.0/0"],
        )
        self._artifact_registry = ArtifactRegistryRepository(
            f"{name}-repository", format=RegistryFormat.DOCKER
        )
        self.deploy_timeout = deploy_timeout
        self._custom_domain: Optional[CustomDomainMapping] = None
        self._ip_address: Optional[GlobalIPAddress] = None
        self._ssl_certificate: Optional[ManagedSSLCertificate] = None
        self.domain = domain
        if self.domain:
            if self._health_check is None:
                raise ValueError("Health check must be provided to use a custom domain")
            self._ip_address = GlobalIPAddress(f"{name}-ip-address")
            self._ssl_certificate = ManagedSSLCertificate(
                f"{name}-ssl-certificate", domains=self.domain
            )
            self._custom_domain = CustomDomainMapping(
                name=f"{name}-domain-mapping",
                ip_address=self._ip_address,
                ssl_certificate=self._ssl_certificate,
                gce_service_backend=GCEServiceBackend(
                    self._mig, self._health_check, "http"
                ),
            )

    def resources(self) -> List[Resource]:
        resources: List[Resource[Any]] = [
            self._mig,
            self._firewall_rule,
            self._artifact_registry,
        ]
        # TODO: always including the health check causes it to show up twice in the plan
        # but if we don't include it then the update to the mig doesn't show up. For
        # now we just show it twice cause it's not the worst thing in the world
        if self._health_check is not None:
            resources.append(self._health_check)
        if self._autoscaler is not None:
            resources.append(self._autoscaler)
        if self._ip_address is not None:
            resources.append(self._ip_address)
        if self._ssl_certificate is not None:
            resources.append(self._ssl_certificate)
        if self._custom_domain is not None:
            resources.append(self._custom_domain)
        return resources

    def inputs(self, *args, **kwargs) -> Inputs:
        return ComputeEngineServiceInputs(
            machine_type=self.machine_type,
            deploy_timeout_sec=self.deploy_timeout.total_seconds(),
            disk_size_gb=self.disk_size_gb,
        )

    def outputs(self) -> ServiceOutputs:
        service_url = "Unsuppported - custom domain required"
        dns_outputs = None
        if self._custom_domain is not None:
            dns_outputs = self._custom_domain.dns_outputs()
            service_url = f"https://{self.domain}"
        return ServiceOutputs(
            service_url=service_url,  # type: ignore
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
    ) -> ComputeEngineServiceReleaseInputs:
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

        return ComputeEngineServiceReleaseInputs(docker_image=docker_image)

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
    ) -> ComputeEngineServiceReleaseInputs:
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

        return ComputeEngineServiceReleaseInputs(docker_image=docker_image)

    async def _release(
        self,
        *,
        release_inputs: ComputeEngineServiceReleaseInputs,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        region = self.region or gcp_environment_config.default_region

        await _release_compute_engine_service(
            docker_image=release_inputs.docker_image,
            machine_type=self.machine_type,
            disk_size_gb=self.disk_size_gb,
            deploy_timeout=self.deploy_timeout,
            gcp_environment_config=gcp_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            service_name=self.name,
            mig_resource_id=self._mig.resource_id,
            region=region,
        )
