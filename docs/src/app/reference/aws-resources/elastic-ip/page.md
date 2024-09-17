## ElasticIP

An Elastic IP address.

### Example Usage
```python
import launchflow as lf

static_ip = lf.aws.ElasticIP("my-static-ip")
```

### initialization

TODO

### inputs

```python
ElasticIP.inputs(environment_state: EnvironmentState) -> ElasticIPInputs
```

Get the inputs required for the Elastic IP service container.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `ElasticIPInputs`: The inputs required for the Elastic IP service container
