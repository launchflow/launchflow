from dataclasses import dataclass
from typing import List, Optional

from launchflow.models.enums import ServiceProduct
from launchflow.node import Node, NodeType, Outputs
from launchflow.resource import Resource


@dataclass
class DNSOutputs(Outputs):
    domain: str
    ip_address: str


@dataclass
class ServiceOutputs(Outputs):
    service_url: str
    docker_repository: str
    dns_outputs: Optional[DNSOutputs]


class Service(Node[ServiceOutputs]):
    product = ServiceProduct.UNKNOWN

    def __init__(
        self,
        name: str,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        super().__init__(name, NodeType.SERVICE)

        self.name = name
        self.dockerfile = dockerfile
        self.build_directory = build_directory
        self.build_ignore = build_ignore

    def outputs(self) -> ServiceOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> ServiceOutputs:
        raise NotImplementedError

    def resources(self) -> List[Resource]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, Service)
            and value.name == self.name
            and value.product == self.product
            and value.inputs() == self.inputs()
            and value.dockerfile == self.dockerfile
            and value.build_directory == self.build_directory
            and value.build_ignore == self.build_ignore
        )
