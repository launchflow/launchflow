from dataclasses import dataclass
from typing import List

from launchflow.node import Node, NodeType, Outputs, T
from launchflow.resource import Resource


@dataclass
class DeploymentOutputs(Outputs):
    deployment_id: str


class Deployment(Node[T]):
    def __init__(self, name: str) -> None:
        super().__init__(name, NodeType.DEPLOYMENT)

    def outputs(self) -> DeploymentOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> DeploymentOutputs:
        raise NotImplementedError

    def resources(self) -> List[Resource]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, Deployment)
            and value.name == self.name
            and value.inputs() == self.inputs()
        )
