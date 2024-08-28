import dataclasses
from typing import Literal, Optional

from typing_extensions import List

from launchflow import exceptions
from launchflow.gcp.http_health_check import HttpHealthCheck
from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class RegionalManagedInstanceGroupOutputs(Outputs):
    pass


@dataclasses.dataclass
class _AutoHealingPolicyInputs(Inputs):
    health_check: str
    initial_delay_sec: int


@dataclasses.dataclass
class AutoHealingPolicy:
    """The policy to fix \"unhealthy\" instances.

    **Args:**
    - `health_check (HttpHealthCheck)`: The [health check](/reference/gcp-resources/http-health-check) to use to determine if an instance is unhealthy.
    - `initial_delay_sec (int)`: The number of seconds to wait before the first health check.
    """

    health_check: HttpHealthCheck
    initial_delay_sec: int


@dataclasses.dataclass
class NamedPort:
    """A namped port on a managed instance group.

    **Args:**
    - `name (str)`: The name of the port.
    - `port (int)`: The port number.
    """

    name: str
    port: int


@dataclasses.dataclass
class UpdatePolicy(Inputs):
    """The policy for updating a managed instance group.

    **Args:**
    - `type (Literal["PROACTIVE", "OPPORTUNISTIC"])`: The type of update.
    - `minimal_action (Literal["NONE", "REFRESH", "RESTART", "REPLACE"])`: The minimal action to take.
    - `most_disruptive_allowed_action (Literal["NONE", "REFRESH", "RESTART", "REPLACE"])`: The most disruptive action allowed.
    - `instance_redistribution_type (Literal["PROACTIVE", "NONE"])`: The type of instance redistribution.
    - `max_surge_fixed (Optional[int])`: The maximum number of instances to add during an update.
    - `max_surge_percentage (Optional[float])`: The maximum percentage of instances to add during an update.
    - `max_unavailable_fixed (Optional[int])`: The maximum number of instances to remove during an update.
    - `max_unavailable_percentage (Optional[float])`: The maximum percentage of instances to remove during an update.
    - `min_ready_sec (Optional[int])`: The minimum number of seconds to wait before marking an instance as ready.
    - `replacement_method (Literal["RECREATE", "SUBSTITUTE"])`: The method to use to replace instances.
    """

    type: Literal["PROACTIVE", "OPPORTUNISTIC"] = "OPPORTUNISTIC"
    minimal_action: Literal["NONE", "REFRESH", "RESTART", "REPLACE"] = "REPLACE"
    most_disruptive_allowed_action: Literal["NONE", "REFRESH", "RESTART", "REPLACE"] = (
        "REPLACE"
    )
    instance_redistribution_type: Literal["PROACTIVE", "NONE"] = "PROACTIVE"
    max_surge_fixed: Optional[int] = None
    max_surge_percentage: Optional[float] = None
    max_unavailable_fixed: Optional[int] = None
    max_unavailable_percentage: Optional[float] = None
    min_ready_sec: Optional[int] = None
    replacement_method: Literal["RECREATE", "SUBSTITUTE"] = "SUBSTITUTE"


@dataclasses.dataclass
class RegionalManagedInstanceGroupInputs(ResourceInputs):
    base_instance_name: str
    target_size: Optional[int]
    region: str
    update_policy: UpdatePolicy
    auto_healing_policy: Optional[_AutoHealingPolicyInputs]
    named_ports: Optional[List[NamedPort]]


class RegionalManagedInstanceGroup(GCPResource[RegionalManagedInstanceGroupOutputs]):
    """A regional managed instance group.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/compute/docs/instance-groups/regional-migs).

    ### Example Usage

    #### Basic Usage

    ```python
    import launchflow as lf

    mig = lf.gcp.RegionalManagedInstanceGroup("regional-mig")
    ```

    #### With Custom Auto-Healing Policy

    ```python
    health_check = lf.gcp.HttpHealthCheck("health-check")
    mig = lf.gcp.RegionalManagedInstanceGroup(
        "regional-mig",
        auto_healing_policy=lf.gcp.regional_managed_instance_group.AutoHealingPolicy(
            health_check=health_check,
            initial_delay_sec=60,
        ),
    )
    ```
    """

    product = ResourceProduct.GCP_REGIONAL_MANAGED_INSTANCE_GROUP.value

    def __init__(
        self,
        name: str,
        *,
        target_size: Optional[int] = None,
        base_instance_name: Optional[str] = None,
        region: Optional[str] = None,
        update_policy: UpdatePolicy = UpdatePolicy(),
        auto_healing_policy: Optional[AutoHealingPolicy] = None,
        named_ports: Optional[List[NamedPort]] = None,
    ):
        """Create a new RegionalManagedInstanceGroup.

        **Args:**
        - `name (str)`: The name of the managed instance group.
        - `target_size (Optional[int])`: The target number of instances.
        - `base_instance_name (Optional[str])`: The base name of the instances.
        - `region (Optional[str])`: The region to create the managed instance group in. If null defaults to the default region of the environment.
        - `update_policy (UpdatePolicy)`: The [policy for updating](#update-policy) the managed instance group.
        - `auto_healing_policy (Optional[AutoHealingPolicy])`: The [policy for auto-healing](#auto-healing-policy) the managed instance group.
        - `named_ports (Optional[List[NamedPort]])`: The [named ports](#named-port) on the managed instance group.
        """
        super().__init__(name)
        self.target_size = target_size
        self.base_instance_name = base_instance_name
        self.region = region
        self.update_policy = update_policy
        self.auto_healing_policy = auto_healing_policy
        self.named_ports = named_ports

    def inputs(
        self, environment_state: EnvironmentState
    ) -> RegionalManagedInstanceGroupInputs:
        if environment_state.gcp_config is None:
            raise exceptions.GCPConfigNotFound(
                "Environment must be configured for GCP to use ManagedInstanceGroup."
            )
        base_instance_name = self.base_instance_name or self.name
        region = self.region or environment_state.gcp_config.default_region
        auto_healing_policy = None
        if self.auto_healing_policy is not None:
            auto_healing_policy = _AutoHealingPolicyInputs(
                health_check=Depends(self.auto_healing_policy.health_check).gcp_id,  # type: ignore
                initial_delay_sec=self.auto_healing_policy.initial_delay_sec,
            )
        return RegionalManagedInstanceGroupInputs(
            resource_id=self.resource_id,
            target_size=self.target_size,
            base_instance_name=base_instance_name,
            region=region,
            update_policy=self.update_policy,
            auto_healing_policy=auto_healing_policy,
            named_ports=self.named_ports,
        )
