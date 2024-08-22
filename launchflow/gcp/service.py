from launchflow.models.enums import CloudProvider
from launchflow.service import Service


class GCPService(Service):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.GCP
