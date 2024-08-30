## ApplicationLoadBalancer

An Application Load Balancer.

**Note:** This Resource is in beta and is likely to change in the future.

For more information see [the official documentation](https://docs.aws.amazon.com/elasticloadbalancing/).

## Example Usage
```python
import launchflow as lf

alb = lf.aws.ApplicationLoadBalancer("my-lb", health_check_path='/health')
```

### initialization

Creates a new Application Load Balancer.

**Args:**
- `name (str)`: The name of the Application Load Balancer.
- `container_port (int)`: The port that the container listens on.
- `health_check_path (Optional[str])`: The path to use for the health check
- `certificate (Optional[ACMCertificate])`: The certificate to use for the ALB.

### inputs

```python
ApplicationLoadBalancer.inputs(environment_state: EnvironmentState) -> ApplicationLoadBalancerInputs
```

Get the inputs for the Application Load Balancer resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for.

**Returns:**
- An `ApplicationLoadBalancerInputs` object containing the inputs for the ALB.
