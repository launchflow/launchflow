## HttpHealthCheck

A health check for a managed instance group.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/load-balancing/docs/health-check-concepts).

### Example Usage

#### Basic Usage
```python
import launchflow as lf

health_check = lf.gcp.HttpHealthCheck("health-check")
```

#### With customization
```python
import launchflow as lf

health_check = lf.gcp.HttpHealthCheck(
    "health-check",
    request_path="/healthz",
    port=8080,
    check_interval_sec=10,
    timeout_sec=10,
    healthy_threshold=3,
    unhealthy_threshold=4,
)
```

### initialization

Create a new HttpHealthCheck.

**Args:**
- `name (str)`: The name of the health check.
- `check_interval_sec (int)`: How often to check the health of the backend.
- `timeout_sec (int)`: How long to wait for a response before failing the check.
- `healthy_threshold (int)`: How many successful checks before marking the backend as healthy.
- `unhealthy_threshold (int)`: How many failed checks before marking the backend as unhealthy.
- `host (str)`: The host header to send with the request. Defauls to the VM attached to the instance.
- `request_path (str)`: The path to send the request to. Defaults to `/`.
- `port (int)`: The port to send the request to. Defaults to `80`.
- `response (str)`: The expected response from the backend. Defaults to `None`.
- `proxy_header (str)`: The proxy header to send with the request. Defaults to `None`.
- `port_specification (str)`: The port specification to use. Defaults to `None`.
