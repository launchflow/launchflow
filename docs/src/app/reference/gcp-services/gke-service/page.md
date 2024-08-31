## GKEService

A service hosted on a GKE Kubernetes Cluster.

Like all [Services](/concepts/services), this class configures itself across multiple [Environments](/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/concepts/service).

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

#### Deploy to GPU Enabled Node Pool
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster", delete_protection=False)
node_pool = lf.gcp.NodePool(
    name="node-pool",
    cluster=cluster,
    machine_type="n1-standard-2",
    guest_accelerators=[lf.gcp.gke.GuestAccelerator(type="nvidia-tesla-t4", count=1)],
)
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
service = lf.gcp.GKEService(
    name="service",
    cluster=cluster,
    node_pool=node_pool,
    tolerations=[lf.kubernetes.service.Toleration(key="nvidia.com/gpu", value="present", operator="Equal")],
)
```

#### Service with a Horizontal Pod Autoscaler

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService(
    "my-service",
    cluster=cluster,
    container_resources=lf.kubernetes.service.ContainerResources(
        requests=lf.kubernetes.service.ResourceQuantity(cpu="0.2"),
    ),
)
hpa = lf.kubernetes.HorizontalPodAutoscaler(
    "hpa",
    cluster=cluster,
    target_name=service.name
)
```

#### Service with a Custom Domain Mapping
```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService(
    "my-service",
    cluster=cluster,
    domain="example.com"
    service_type="NodePort",
)
```

### initialization

Create a new GKE Service.

**Args:**
- `name (str)`: The name of the service.
- `cluster (GKECluster)`: The [GKE cluster](/reference/gcp-resources/gke#gke-cluster) to deploy the service to.
- `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
- `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
- `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
- `node_pool (Optional[NodePool])`: The [node pool](/reference/gcp-resources/gke#node-pool) to deploy the service to.
- `container_port (int)`: The port the service will listen on inside the container.
- `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
- `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
- `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
- `startup_probe (Optional[StartupProbe])`: The [startup probe](/reference/kubernetes-resources/service#startup-probe) for the service.
- `liveness_probe (Optional[LivenessProbe])`: The [liveness probe](/reference/kubernetes-resources/service#liveness-probe) for the service.
- `readiness_probe (Optional[ReadinessProbe])`: The [readiness probe](/reference/kubernetes-resources/service#readiness-probe) for the service.
- `environment_variables (Optional[Dict[str, str]])`: A dictionary of environment variables to set on the service container.
- `container_resources (Optional[ContainerResources])`: The [container resources](/reference/kubernetes-resources/service#container-resources) for the service. NOTE: If you are creating a [HorizontalPodAutoscaler](/reference/kubernetes-resources/hpa) you will need to provide this.
- `tolerations (Optional[List[Toleration]])`: A list of [tolerations](/reference/kubernetes-resources/service#toleration) for the service.
- `domain (Optional[str])`: The domain to use for the service. `service_type` must be `NodePort` to assign a custom domain.
