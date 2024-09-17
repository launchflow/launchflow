from launchflow.models.enums import CloudProvider
from launchflow.service import DockerService, Service, ServiceOutputs


class GCPService(Service[ServiceOutputs]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.GCP


class GCPDockerService(DockerService, GCPService):
    pass
