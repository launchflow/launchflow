## LambdaEventMapping

A mapping between an event source and a Lambda function.

****Example usage:****
```python
import launchflow as lf

mapping = lf.aws.LambdaEventMapping("my-event-mapping")
```

### initialization

TODO

### inputs

```python
LambdaEventMapping.inputs(environment_state: EnvironmentState) -> LambdaEventMappingInputs
```

Get the inputs for the Lambda event mapping resource.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `LambdaEventMappingInputs`: The inputs required for the Lambda event mapping
