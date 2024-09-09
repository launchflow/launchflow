import dataclasses
from datetime import timedelta
from typing import Any, List, Literal, Optional, Union

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
from launchflow.gcp.service import GCPDockerService
from launchflow.gcp.ssl import ManagedSSLCertificate
from launchflow.models.enums import ServiceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DockerServiceOutputs


@dataclasses.dataclass
class ComputeEngineServiceInputs(Inputs):
    machine_type: str
    disk_size_gb: int
    deploy_timeout_sec: float


class ComputeEngineService(GCPDockerService):
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
            dockerfile=dockerfile,
            build_directory=build_directory,
            build_ignore=build_ignore,
        )
        self.machine_type = machine_type
        self.port = port
        self.region = region
        self.disk_size_gb = disk_size_gb

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
        if self._custom_domain is not None:
            resources.append(self._custom_domain)
        return resources

    def inputs(self, *args, **kwargs) -> Inputs:
        return ComputeEngineServiceInputs(
            machine_type=self.machine_type,
            deploy_timeout_sec=self.deploy_timeout.total_seconds(),
            disk_size_gb=self.disk_size_gb,
        )

    def outputs(self) -> DockerServiceOutputs:
        repo_outputs = self._artifact_registry.outputs()
        if repo_outputs.docker_repository is None:
            raise ValueError("Docker repository not found in artifact registry outputs")
        service_url = None
        dns_outputs = None
        if self._custom_domain is not None:
            dns_outputs = self._custom_domain.dns_outputs()
            service_url = f"https://{self.domain}"
        return DockerServiceOutputs(
            service_url=service_url,  # type: ignore
            docker_repository=repo_outputs.docker_repository,
            dns_outputs=dns_outputs,
        )
