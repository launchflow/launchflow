## ServiceContainer

A container for a service running on a Kubernetes cluster.

NOTE: ServiceContainer is still in beta and is subject to change.

This will create a deployment and a service containing that deployment on the Kubernetes cluster.

### Example usage

#### Basic Usage

```python
import launchflow as lf

cluster = lf.gke.GKECluster("my-cluster")
container = lf.kubernetes.ServiceContainer("my-service")
```

#### Custom Image

```python
import launchflow as lf

cluster = lf.gke.GKECluster("my-cluster")
container = lf.kubernetes.ServiceContainer("my-service", image="nginx")
```

### initialization

Create a new ServiceContainer.

**Args:**
- `name (str)`: The name of the service.
- `cluster (GKECluster)`: The [GKE cluster](/docs/reference/gcp-resources/gke#gke-cluster) to deploy the service to.
- `namespace (str)`: The Kubernetes namespace to deploy the service to. Defaults to `default`. The `default` namespace is connected to your LaunchFlow environment automatically, we recommend leaving this as default unless you need to deploy an isolated service.
- `num_replicas`: The number of replicas to start.
- `node_pool (Optional[NodePool])`: The [node pool](/docs/reference/gcp-resources/gke#node-pool) to deploy the service to.
- `image (str)`: The Docker image to user for the deployment. Defaults to `httpd`.
- `container_port (int)`: The port the service will listen on inside the container.
- `host_port (Optional[int])`: The port the service will listen on outside the container. If not provided, the service will not be exposed outside the cluster.
- `startup_probe (Optional[StartupProbe])`: The [startup probe](#startup-probe) for the service.
- `liveness_probe (Optional[LivenessProbe])`: The [liveness probe](#liveness-probe) for the service.
- `readiness_probe (Optional[ReadinessProbe])`: The [readiness probe](#readiness-probe) for the service.
- `service_type (Literal["ClusterIP", "NodePort", "LoadBalancer"])`: The type of Kubernetes service to create. Defaults to `LoadBalancer`.
- `container_resources (Optional[ContainerResources])`: The [container resources](#container-resources) for the service. NOTE: If you are creating a [HorizontalPodAutoscaler](/docs/reference/kubernetes-resources/horizonal-pod-autoscaler) you will need to provide this.
- `tolerations (Optional[List[Toleration]])`: A list of [tolerations](#tolerations) for the service.
- `annotations (Optional[Dict[str, str]])`: A dictionary of annotations to add to the service.

## Toleration

A Kubernetes toleration applied to a service.

**Args:**
- `key (str)`: The key to match against.
- `value (str)`: The value to match against.
- `operator (Literal["Equal", "Exists"])`: The operator to use.
- `effect (Optional[str])`: The effect to apply.

## ResourceQuantity

Resource information for a Kubernetes container.

**Args:**
- `cpu (str)`: The CPU limit or request.
- `memory (str)`: The memory limit or request.

## ContainerResources

ContainerResources used by a Kubernetes container.

**Args:**
- `limit (ContainerResourceInputs)`: The resource limits for the container.
- `request (ContainerResourceInputs)`: The resource requests for the container.

## HTTPGet

An HTTPGet used by a Kubernetes probe.

**Args:**
- `path (str)`: The endpoint the probe should call.
- `port (int)`: The port to probe.

## StartupProbe

A StartupProbe used by a Kubernetes container.

**Args:**
- `http_get (HTTPGet)`: The HTTPGet probe to use.
- `failure_threshold (int)`: The number of failures before the probe is considered failed.
- `period_seconds (int)`: The number of seconds between probe checks.

## LivenessProbe

A LivenessProbe used by a Kubernetes container.

**Args:**
- `http_get (HTTPGet)`: The HTTPGet probe to use.
- `initial_delay_seconds (int)`: The number of seconds to wait before starting probes.
- `period_seconds (int)`: The number of seconds between probe checks.

## ReadinessProbe

A LivenessProbe used by a Kubernetes container.

**Args:**
- `http_get (HTTPGet)`: The HTTPGet probe to use.
- `initial_delay_seconds (int)`: The number of seconds to wait before starting probes.
- `period_seconds (int)`: The number of seconds between probe checks.
