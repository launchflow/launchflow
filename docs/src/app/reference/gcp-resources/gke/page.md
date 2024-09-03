## GKECluster

A Kubernetes Cluster hosted on GKE.

NOTE: GKECluster is still in beta and is subject to change.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/kubernetes-engine).

When a GKE cluster is created in an environment, LaunchFlow will connect the default namespace to the environment service account. This ensures that
all service, workers, and jobs in the default namespace can access resources in the environment. If you would like to deploy and isolated service, worker, or
job we recommend using a new namespace.

### Example Usage

#### Create a GKE Cluster and Deploy a Service

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
service = lf.gcp.GKEService("my-service", cluster=cluster)
```

#### Create a Regional Cluster

Force a regional cluster. By default LaunchFlow will use regional clusters for production environments and zonal clusters for development environments.

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster", regional=True, region="us-west1")
```

#### Create a Single Zone Cluster

Force a singl zone cluster. By default LaunchFlow will use regional clusters for production environments and zonal clusters for development environments.

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster", regional=False, zones="us-west1")
```

#### Specify a Subnet

If you create multiple clusters in your environment it is recommened you provide a custom IP range for the subnet for each cluster.

```python
import launchflow as lf

cluster1 = lf.gcp.GKECluster("my-cluster1", subnet_ip_cidr_range="10.90.0.0/20")
cluster2 = lf.gcp.GKECluster("my-cluster2", subnet_ip_cidr_range="10.50.0.0/20")
```

### initialization

Creates a new GKE Cluster.

**Args:**
- `name (str)`: The name of the GKE cluster.
- `subnet_ip_cidr_range (str)`: The IP range for the cluster's subnet.
- `pod_ip_cidr_range (str)`: The IP range for the cluster's pods.
- `service_cidr_range (str)`: The IP range for the cluster's services.
- `regional (Optional[bool])`: Whether the cluster is regional or zonal. If not provided will default to True for production environments and False for development environments.
- `region (Optional[str])`: The region for the cluster. If not provided will default to the default region for the environment.
- `zones (Optional[List[str]])`: The zones for the cluster. If not provided will default to the default zone for development environments, and remain unset for production environments.
- `delete_protection (bool)`: Whether the cluster should have delete protection enabled.
- `enable_tpu (bool)`: Whether the cluster should have TPU resources enabled. WARNING: This changing this will delete and recreate the cluster. Defaults to False. Defaults to False.

## NodePool

A node pool for a GKE cluster.

NOTE: This resource is currently in beta and may change in the future.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools).

### Example Usage

#### Basic Example

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")
```

#### Autoscaling Example

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
autoscaling = lf.gcp.gke.Autoscaling(min_node_count=1, max_node_count=10)
node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro", autoscaling=autoscaling)
```

#### Deploy Service to Node Pool

```python
import launchflow as lf

cluster = lf.gcp.GKECluster("my-cluster")
node_pool = lf.gcp.NodePool("my-node-pool", cluster=cluster, machine_type="e2-micro")

service = lf.gcp.GKEService("my-service", cluster=cluster, node_pool=node_pool)
```

## Autoscaling

Autoscaling configurate for a GKE Node Pool.

**Args:***
- `min_node_count (int)`: The minimum number of nodes per zone in the node pool. Cannot be used with the `total_*` limits.
- `max_node_count (int)`: The maximum number of nodes per zone in the node pool. Cannot be used with the `total_*` limits.
- `total_min_node_count (int)`: The minimum number of nodes in the node pool. Cannot be used with the zone limits.
- `total_max_node_count (int)`: The maximum number of nodes in the node pool. Cannot be used with the zone limits.
