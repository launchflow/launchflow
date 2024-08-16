## RegionalManagedInstanceGroup

A regional managed instance group.

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

### initialization

Create a new RegionalManagedInstanceGroup.

**Args:**
- `name (str)`: The name of the managed instance group.
- `target_size (Optional[int])`: The target number of instances.
- `base_instance_name (Optional[str])`: The base name of the instances.
- `region (Optional[str])`: The region to create the managed instance group in. If null defaults to the default region of the environment.
- `update_policy (UpdatePolicy)`: The [policy for updating](#update-policy) the managed instance group.
- `auto_healing_policy (Optional[AutoHealingPolicy])`: The [policy for auto-healing](#auto-healing-policy) the managed instance group.
- `named_ports (Optional[List[NamedPort]])`: The [named ports](#named-port) on the managed instance group.

## AutoHealingPolicy

The policy to fix "unhealthy" instances.

**Args:**
- `health_check (HttpHealthCheck)`: The [health check](/reference/gcp-resources/http-health-check) to use to determine if an instance is unhealthy.
- `initial_delay_sec (int)`: The number of seconds to wait before the first health check.

## NamedPort

A namped port on a managed instance group.

**Args:**
- `name (str)`: The name of the port.
- `port (int)`: The port number.

## UpdatePolicy

The policy for updating a managed instance group.

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
