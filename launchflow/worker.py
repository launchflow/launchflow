from dataclasses import dataclass
from typing import List

from launchflow.deployment import Deployment, DeploymentOutputs


@dataclass
class WorkerOutputs(DeploymentOutputs):
    docker_repository: str


class Worker(Deployment[WorkerOutputs]):
    def __init__(
        self,
        name: str,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        super().__init__(name)

        self.name = name
        self.dockerfile = dockerfile
        self.build_directory = build_directory
        self.build_ignore = build_ignore

    def outputs(self) -> WorkerOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> WorkerOutputs:
        raise NotImplementedError

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, Worker)
            and value.name == self.name
            and value.product == self.product
            and value.inputs() == self.inputs()
            and value.dockerfile == self.dockerfile
            and value.build_directory == self.build_directory
            and value.build_ignore == self.build_ignore
        )
