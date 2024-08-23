from dataclasses import dataclass
from typing import List, Optional

from launchflow.deployment import Deployment, DeploymentOutputs, T
from launchflow.models.enums import ServiceProduct
from launchflow.node import Outputs


@dataclass
class ServiceOutputs(DeploymentOutputs):
    service_url: str


class Service(Deployment[T]):
    product = ServiceProduct.UNKNOWN

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

    def outputs(self) -> ServiceOutputs:
        raise NotImplementedError

    async def outputs_async(self) -> ServiceOutputs:
        raise NotImplementedError

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


# TODO: Determine if we can remove the Outputs inheritance for DNSOutputs
@dataclass
class DNSOutputs(Outputs):
    domain: str
    ip_address: str


@dataclass
class DockerServiceOutputs(ServiceOutputs):
    docker_repository: str
    dns_outputs: Optional[DNSOutputs]


class DockerService(Service[T]):
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


@dataclass
class StaticServiceOutputs(ServiceOutputs):
    dns_outputs: Optional[DNSOutputs]


class StaticService(Service[T]):
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
