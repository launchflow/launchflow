from typing import Optional, Set

from launchflow.gcp.gke import GKECluster
from launchflow.models.enums import CloudProvider
from launchflow.tofu import T, TofuResource


class KubernetesResource(TofuResource[T]):
    def __init__(
        self,
        name: str,
        cluster: GKECluster,
        replacement_arguments: Optional[Set[str]] = None,
        resource_id: Optional[str] = None,
        ignore_arguments: Optional[Set[str]] = None,
    ):
        super().__init__(name, replacement_arguments, resource_id, ignore_arguments)
        self.cluster = cluster

    def cloud_provider(self) -> CloudProvider:
        if isinstance(self.cluster, GKECluster):
            return CloudProvider.GCP
        else:
            raise NotImplementedError
