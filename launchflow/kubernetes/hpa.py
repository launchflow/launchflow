import dataclasses
from typing import List, Literal, Optional

from launchflow.gcp.gke import GKECluster
from launchflow.kubernetes.resource import KubernetesResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class ResourceMetric(Inputs):
    name: str
    target_type: Literal["Utilization", "AverageValue", "Value"]
    target_average_value: Optional[str] = None
    target_average_utilization: Optional[str] = None
    target_value: Optional[str] = None


@dataclasses.dataclass
class HorizonalPodAutoscalerInputs(ResourceInputs):
    cluster_id: str
    k8_provider: Literal["gke", "eks"]
    namespace: str
    min_replicas: int
    max_replicas: int
    target_name: str
    # TODO: add support for additional metric types
    resource_metrics: List[ResourceMetric]


@dataclasses.dataclass
class HorizontalPodAutoscalerOutputs(Outputs):
    pass


class HorizontalPodAutoscaler(KubernetesResource[HorizontalPodAutoscalerOutputs]):
    """An autoscaler for a Kubernetes service.

    NOTE: HorizontalPodAutoscaler is still in beta and is subject to change.

    ### Example usage
    """

    product = ResourceProduct.KUBERNETES_HORIZONTAL_POD_AUTOSCALER.value

    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        target_name: str,
        *,
        namespace: str = "default",
        min_replicas: int = 1,
        max_replicas: int = 10,
        resource_metrics: List[ResourceMetric] = [
            ResourceMetric(
                name="cpu", target_type="Utilization", target_average_utilization="60"
            )
        ],
    ):
        super().__init__(name, cluster)
        self.namespace = namespace
        self.target_name = target_name
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.resource_metrics = resource_metrics

    def inputs(
        self, environment_state: EnvironmentState
    ) -> HorizonalPodAutoscalerInputs:
        cluster_id = None
        k8_provider = None
        if isinstance(self.cluster, GKECluster):
            cluster_id = Depends(self.cluster).gcp_id  # type: ignore
            k8_provider = "gke"
        else:
            raise NotImplementedError("Only GKE clusters are supported at this time.")
        return HorizonalPodAutoscalerInputs(
            resource_id=self.resource_id,
            cluster_id=cluster_id,
            k8_provider=k8_provider,  # type: ignore
            namespace=self.namespace,
            min_replicas=self.min_replicas,
            max_replicas=self.max_replicas,
            target_name=self.target_name,
            resource_metrics=self.resource_metrics,
        )
