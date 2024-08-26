from dataclasses import dataclass

from launchflow.models.enums import CloudProvider
from launchflow.service import DockerService, Service, ServiceOutputs, StaticService, T


@dataclass
class AWSServiceOutputs(ServiceOutputs):
    code_build_project_name: str


class AWSService(Service[T]):
    def outputs(self) -> AWSServiceOutputs:
        raise NotImplementedError

    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS


class AWSDockerService(DockerService, AWSService):
    pass


class AWSStaticService(StaticService, AWSService):
    pass
