## NATGateway

A NAT Gateway

### Example Usage
```python
import launchflow as lf

nat = lf.aws.NATGateway("my-nat-gateway")
```

### initialization

TODO

### inputs

```python
NATGateway.inputs(environment_state: EnvironmentState) -> NATGatewayInputs
```

Get the inputs required for the NAT Gateway.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `NATGatewayInputs`: The inputs required for the NAT Gateway
