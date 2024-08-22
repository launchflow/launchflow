from typing import Optional, Set

from launchflow.models.enums import CloudProvider
from launchflow.tofu import T, TofuResource


class GCPResource(TofuResource[T]):
    def __init__(
        self,
        name: str,
        replacement_arguments: Optional[Set[str]] = None,
        resource_id: Optional[str] = None,
        ignore_arguments: Optional[Set[str]] = None,
    ):
        super().__init__(name, replacement_arguments, resource_id, ignore_arguments)

    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.GCP
