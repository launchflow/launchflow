## HorizontalPodAutoscaler

An autoscaler for a Kubernetes service.

NOTE: HorizontalPodAutoscaler is still in beta and is subject to change.

### Example usage

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

### initialization

Create a new HorizontalPodAutoscaler.

**Args:**
- `name (str)`: The name of the resource.
- `cluster (GKECluster)`: The cluster to create the resource in.
- `target_name (str)`: The name of the target deployment.
- `namespace (str)`: The namespace to create the resource in. Default is "default".
- `min_replicas (int)`: The minimum number of replicas. Default is 1.
- `max_replicas (int)`: The maximum number of replicas. Default is 10.
- `resource_metrics (List[ResourceMetric])`: List [ResourceMetrics](#resource-metric) to use for scaling. Default is CPU utilization at 60%.
