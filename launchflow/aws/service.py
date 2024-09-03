from dataclasses import dataclass

from launchflow.models.enums import CloudProvider
from launchflow.service import (
    DockerService,
    DockerServiceOutputs,
    Service,
    StaticService,
    T,
)


class AWSService(Service[T]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS


@dataclass
class AWSDockerServiceOutputs(DockerServiceOutputs):
    code_build_project_name: str


class AWSDockerService(DockerService, AWSService):
    def outputs(self) -> AWSDockerServiceOutputs:
        raise NotImplementedError


class AWSStaticService(StaticService, AWSService):
    pass
