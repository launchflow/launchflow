from launchflow.models.enums import CloudProvider
from launchflow.service import DockerService, Service, StaticService, T


class GCPService(Service[T]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.GCP


class GCPDockerService(DockerService, GCPService):
    pass


class GCPStaticService(StaticService, GCPService):
    pass
