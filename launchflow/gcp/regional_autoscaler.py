import dataclasses
from typing import List, Literal

from typing_extensions import Optional

from launchflow.gcp.regional_managed_instance_group import RegionalManagedInstanceGroup
from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class RegionalAutoscalerInputs(ResourceInputs):
    instance_group_manager_id: str
    region: Optional[str]
    autoscaling_policies: List["AutoscalingPolicy"]


@dataclasses.dataclass
class RegionalAutoscalerOutputs(Outputs):
    pass


class RegionalAutoscaler(GCPResource[RegionalAutoscalerOutputs]):
    """A regional autoscaler for a regional managed instance group.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/compute/docs/autoscaler).

    ### Example Usage

    #### Basic Usage

    This will scale based on CPU utilization of .6.

    ```python
    import launchflow as lf

    instance_group = lf.gcp.RegionalManagedInstanceGroup("instance-group")
    autoscaler = lf.gcp.RegionalAutoscaler("autoscaler", group_mananger=instance_group)
    ```

    #### Autoscaling based on a specific CPU Utilization

    ```python
    import launchflow as lf

    instance_group = lf.gcp.RegionalManagedInstanceGroup("instance-group")
    autoscaler = lf.gcp.RegionalAutoscaler(
        "autoscaler",
        group_mananger=instance_group,
        autoscaling_policies=[
            lf.gcp.regional_autoscaler.AutoscalingPolicy(
                min_replicas=1,
                max_replicas=10,
                cpu_utilization=lf.gcp.regional_autoscaler.CPUUtilization(target=0.8)
            )
        ]
    )
    ```

    #### Autoscaling based on a custom metric

    ```python
    import launchflow as lf

    instance_group = lf.gcp.RegionalManagedInstanceGroup("instance-group")
    autoscaler = lf.gcp.RegionalAutoscaler(
        "autoscaler",
        group_mananger=instance_group,
        autoscaling_policies=[
            lf.gcp.regional_autoscaler.AutoscalingPolicy(
                min_replicas=1,
                max_replicas=10,
                custom_metric=lf.gcp.regional_autoscaler.CustomMetric(name="my-custom-metric", target=100)
            )
        ]
    )
    ```

    """

    product = ResourceProduct.GCP_REGIONAL_AUTOSCALER.value

    def __init__(
        self,
        name: str,
        *,
        group_manager: RegionalManagedInstanceGroup,
        autoscaling_policies: List["AutoscalingPolicy"],
    ):
        """Create a new regional autoscaler.

        **Args:**
        - `name (str)`: The name of the regional autoscaler.
        - `group_manager (RegionalManagedInstanceGroup)`: The [regional managed instance group](/reference/gcp-resources/regional-managed-instance-group) to scale.
        - `autoscaling_policies (List[AutoscalingPolicy])`: The [autoscaling policies](#autoscaling-policy) to apply.
        """
        super().__init__(name)
        self.group_manager = group_manager
        self.autoscaling_policies = autoscaling_policies

    def inputs(self, environment_state: EnvironmentState) -> RegionalAutoscalerInputs:
        region = (
            self.group_manager.region or environment_state.gcp_config.default_region  # type: ignore
        )
        return RegionalAutoscalerInputs(
            resource_id=self.resource_id,
            instance_group_manager_id=Depends(self.group_manager).gcp_id,  # type: ignore
            region=region,
            autoscaling_policies=self.autoscaling_policies,
        )


@dataclasses.dataclass
class CPUUtilization(Inputs):
    """Configuration for autoscaling based on CPU utilization.
    **Args:**
    - `target (float)`: The target CPU utilization that the autoscaler should aim for. Must be between 0 and 1. Defaults to 0.6.
    - `predictive_method (Literal["NONE", "OPTIMIZE_AVAILABILITY"])`: The predictive method to use for the autoscaler. Defaults to "NONE".
    """

    target: float
    predictive_method: Literal["NONE", "OPTIMIZE_AVAILABILITY"] = "NONE"


@dataclasses.dataclass
class CustomMetric(Inputs):
    """Configuration for autoscaling based on a custom metric.

    **Args:**
    - `name (str)`: The name of the custom metric.
    - `target (Optional[float])`: The target value for the custom metric that the autoscaler should aim for.
    - `type (Optional[Literal["GAUGE", "DELTA_PER_SECOND", "DELTA_PER_MINUTE"]])`: How the target utilization value should be interpreted for a Google Cloud Monitoring metric.
    """

    name: str
    target: Optional[float] = None
    type: Optional[Literal["GAUGE", "DELTA_PER_SECOND", "DELTA_PER_MINUTE"]] = None


@dataclasses.dataclass
class LoadBalancingUtilization:
    """Configuration for autoscaling based on load balancer.

    **Args:**
    - `target (float)`: The percent of backend utilization the autoscaler should aim for. Must be between 0 and 1. Defaults to 0.8.
    """

    target: float


@dataclasses.dataclass
class AutoscalingPolicy(Inputs):
    """The autoscaling policy for a regional autoscaler.

    **Args:**
    - `min_replicas (int)`: The minimum number of instances that the group manager will maintain.
    - `max_replicas (int)`: The maximum number of instances that the group manager will maintain.
    - `cooldown_period (int)`: The number of seconds that the autoscaler should wait before it starts collecting information from a new instance.
    - `cpu_utilization (Optional[CPUUtilization])`: If set the autoscaler will scale based on CPU utilization. This is the default if none of the other options are set.
    - `custom_metric (Optional[CustomMetric])`: If set the autoscaler will scale based on a custom metric you provide (i.e. a pub/sub backlog).
    - `load_balancing_utilization (Optional[LoadBalancingUtilization])`: If set the autoscaler will scale based on the load balancing utilization.
    """

    min_replicas: int
    max_replicas: int
    cooldown_period: Optional[int] = None
    cpu_utilization: Optional[CPUUtilization] = None
    custom_metric: Optional[CustomMetric] = None
    load_balancing_utilization: Optional[LoadBalancingUtilization] = None
