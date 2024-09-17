## CloudRunServiceContainer

A container for a service running on Cloud Run.

### Example usage
```python
import launchflow as lf

service_container = lf.gcp.CloudRunServiceContainer("my-service-container", cpu=4)
```

### initialization

Creates a new Cloud Run Service container.

**Args:**
- `name (str)`: The name of the service.
- `region (Optional[str])`: The region to deploy the service to.
- `cpu (Optional[int])`: The number of CPUs to allocate to each instance of the service.
- `memory (Optional[str])`: The amount of memory to allocate to each instance of the service.
- `port (Optional[int])`: The port the service listens on.
- `publicly_accessible (Optional[bool])`: Whether the service is publicly accessible. Defaults to True.
- `min_instance_count (Optional[int])`: The minimum number of instances to keep running.
- `max_instance_count (Optional[int])`: The maximum number of instances to run.
- `max_instance_request_concurrency (Optional[int])`: The maximum number of requests each instance can handle concurrently.
- `invokers (Optional[List[str]])`: A list of invokers that can access the service.
- `custom_audiences (Optional[List[str]])`: A list of custom audiences that can access the service. See: [https://cloud.google.com/run/docs/configuring/custom-audiences](https://cloud.google.com/run/docs/configuring/custom-audiences)
- `ingress (Optional[Literal])`: The ingress settings for the service. See: [https://cloud.google.com/run/docs/securing/ingress](https://cloud.google.com/run/docs/configuring/custom-audiences)
- `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set for the service.
