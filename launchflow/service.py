from dataclasses import dataclass
from typing import List, Literal, Optional

from launchflow.models.enums import ServiceProduct
from launchflow.node import Node, NodeType, Outputs, T
from launchflow.resource import Resource


@dataclass
class DNSRecord(Outputs):
    dns_record_value: str
    dns_record_type: Literal["A", "TXT"] = "A"


@dataclass
class DNSOutputs(Outputs):
    domain: str
    dns_records: List[DNSRecord]


@dataclass
class ServiceOutputs(Outputs):
    service_url: str
    dns_outputs: Optional[DNSOutputs]


class Service(Node[T]):
    product = ServiceProduct.UNKNOWN.value

    def __init__(self, name: str) -> None:
        super().__init__(name, NodeType.SERVICE)

        self.name = name

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
        )


@dataclass
class DockerServiceOutputs(ServiceOutputs):
    docker_repository: str


class DockerService(Service[ServiceOutputs]):
    def __init__(
        self,
        name: str,
        *,
        dockerfile: str = "Dockerfile",
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        super().__init__(name)

        self.name = name
        self.dockerfile = dockerfile
        self.build_directory = build_directory
        self.build_ignore = build_ignore

    def outputs(self) -> DockerServiceOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> DockerServiceOutputs:
        raise NotImplementedError

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, DockerService)
            and value.name == self.name
            and value.product == self.product
            and value.inputs() == self.inputs()
            and value.dockerfile == self.dockerfile
            and value.build_directory == self.build_directory
            and value.build_ignore == self.build_ignore
        )


@dataclass
class StaticServiceOutputs(ServiceOutputs):
    pass


class StaticService(Service[StaticServiceOutputs]):
    def __init__(
        self,
        name: str,
        static_directory: str,
        *,
        static_ignore: List[str] = [],  # type: ignore
    ) -> None:
        super().__init__(name)

        self.name = name
        self.static_directory = static_directory
        self.static_ignore = static_ignore

    def outputs(self) -> StaticServiceOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> StaticServiceOutputs:
        raise NotImplementedError

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, StaticService)
            and value.name == self.name
            and value.product == self.product
            and value.inputs() == self.inputs()
            and value.static_directory == self.static_directory
            and value.static_ignore == self.static_ignore
        )
