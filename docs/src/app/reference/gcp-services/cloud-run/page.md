## CloudRun

A service hosted on GCP Cloud Run.

### Example Usage
```python
import launchflow as lf

service = lf.gcp.CloudRun("my-service", cpu=4)
```

**NOTE:** This will create the following infrastructure in your GCP project:
- A [Cloud Run](https://cloud.google.com/run) service with the specified configuration.
- A [Load Balancer](https://cloud.google.com/load-balancing) to route traffic to the service.
- A [Cloud Build](https://cloud.google.com/build) trigger that builds and deploys the service.
- An [Artifact Registry](https://cloud.google.com/artifact-registry) repository to store the service's Docker image.

### initialization

Creates a new Cloud Run service.

**Args:**
- `name (str)`: The name of the service.
- `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
- `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
- `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
- `region (Optional[str])`: The region to deploy the service to.
- `cpu (Optional[int])`: The number of CPUs to allocate to each instance of the service.
- `memory (Optional[str])`: The amount of memory to allocate to each instance of the service.
- `port (Optional[int])`: The port the service listens on.
- `publicly_accessible (Optional[bool])`: Whether the service is publicly accessible. Defaults to True.
- `min_instance_count (Optional[int])`: The minimum number of instances to keep running.
- `max_instance_count (Optional[int])`: The maximum number of instances to run.
- `max_instance_request_concurrency (Optional[int])`: The maximum number of requests each instance can handle concurrently.
- `invokers (Optional[List[str]])`: A list of invokers that can access the service.
- `custom_audiences (Optional[List[str]])`: A list of custom audiences that can access the service. See: [https://cloud.google.com/run/docs/configuring/custom-audiences](https://cloud.google.com/run/docs/configuring/custom-audiences).
- `ingress (Optional[Literal["INGRESS_TRAFFIC_ALL", "INGRESS_TRAFFIC_INTERNAL_ONLY", "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"]])`: The ingress settings for the service. See: [https://cloud.google.com/run/docs/securing/ingress](https://cloud.google.com/run/docs/configuring/custom-audiences).
- `domain (Optional[str])`: The custom domain to map to the service.
