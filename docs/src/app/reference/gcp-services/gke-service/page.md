## GKEService

A service hosted on a GKE Kubernetes Cluster.

Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/service).

### Example Usage

#### Basic Usage
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService("my-service", cluster=cluster)
```

#### Custom Dockerfile Path
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService(
    "my-service",
    cluster=cluster,
    dockerfile="docker/Dockerfile"m
    build_directory="path/to/service_dir",
)
```

#### Use a Custom Node Pool
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")

service = lf.gcp.GKEService("my-service", cluster=cluster, node_pool=node_pool)
```

#### Service with a Startup Probe
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService(
    "my-service",
    cluster=cluster,
    startup_probe=lf.kubernetes.StartupProbe(
        path="/healthz",
        initial_delay_seconds=5,
        period_seconds=10,
    ),
)
```

### initialization

Create a new GKE Service.

**Args:**
- `name (str)`: The name of the service.
- `cluster ([GKECluster](/docs/reference/gcp-resources/gke#gke-cluster))`: The GKE cluster to deploy the service to.
- `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
- `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
- `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
- `node_pool ([NodePool](/docs/reference/gcp-resources/gke#node-pool))`: The node pool to deploy the service to. If not provided, the default node pool will be used.
- `container_port (int)`: The port the service will listen on inside the container.
- `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
- `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
- `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
- `startup_probe ([StartupProbe](/docs/reference/kubernetes-resources/service-container#startup-probe))`: The startup probe for the service.
- `liveness_probe ([LivenessProbe](/docs/reference/kubernetes-resources/service-container#liveness-probe))`: The liveness probe for the service.
- `readiness_probe ([ReadinessProbe](/docs/reference/kubernetes-resources/service-container#readiness-probe))`: The readiness probe for the service.
- `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set on the service container.
