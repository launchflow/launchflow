from dataclasses import dataclass

from launchflow.models.enums import CloudProvider
from launchflow.service import Service, ServiceOutputs


@dataclass
class AWSServiceOutputs(ServiceOutputs):
    code_build_project_name: str


class AWSService(Service):
    def outputs(self) -> AWSServiceOutputs:
        raise NotImplementedError

    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS
