## ECSCluster

An ECS cluster.

### Example Usage
```python
import launchflow as lf

ecs_cluster = lf.aws.ECSCluster("my-cluster")
```

### initialization

Creates a new ECS cluster.

**Args:**
- `name (str)`: The name of the ECS cluster.

### inputs

```python
ECSCluster.inputs(environment_state: EnvironmentState) -> ECSClusterInputs
```

Get the inputs for the ECS cluster resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for.

**Returns:**
- An `ECSClusterInputs` object containing the inputs for the ECS cluster.
