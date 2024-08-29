## ECSFargateServiceContainer

A container for a service running on ECS Fargate.

****Example usage:****
```python
import launchflow as lf

service_container = lf.aws.ECSFargateServiceContainer("my-service-container")
```

### initialization

Creates a new ECS Fargate service container.

**Args:**
- `name (str)`: The name of the ECS Fargate service container.
- `ecs_cluster (Union[ECSCluster, str])`: The ECS cluster or the name of the ECS cluster.
- `port (int)`: The port the container listens on. Defaults to 80.
- `desired_count (int)`: The number of tasks to run. Defaults to 1.

**Raises:**
 - `ValueError`: If `ecs_cluster` is not an instance of `ECSCluster` or `str`.

### inputs

```python
ECSFargateServiceContainer.inputs(environment_state: EnvironmentState) -> ECSFargateServiceContainerInputs
```

Get the inputs for the ECS Fargate service container resource.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `ECSFargateServiceContainerInputs`: The inputs required for the ECS Fargate service container.
