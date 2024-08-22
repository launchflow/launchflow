from typing import Dict, Optional

import launchflow
from launchflow import exceptions
from launchflow.clients.docker_client import DockerClient
from launchflow.managers.docker_resource_manager import base64_to_dict
from launchflow.models.enums import CloudProvider, ResourceProduct
from launchflow.node import Inputs
from launchflow.resource import Resource, T


class DockerResource(Resource[T]):
    product = ResourceProduct.LOCAL_DOCKER.value

    def __init__(
        self,
        name: str,
        docker_image: str,
        env_vars: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
        ports: Optional[Dict[str, int]] = None,
        running_container_id: Optional[str] = None,
    ):
        super().__init__(name)
        self.docker_image = docker_image
        self.env_vars = env_vars or {}
        self.command = command

        self.ports = ports or {}
        self.running_container_id = running_container_id

    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.UNKNOWN

    def _lazy_load_container_info(self) -> None:
        """Lazy-load the information about the running container."""
        if None not in self.ports.values():
            return

        try:
            connection_info = self.outputs()
            self.running_container_id = connection_info.container_id  # type: ignore
            self.ports.update(connection_info.ports)  # type: ignore
        except Exception:
            return

    def inputs(self, *args, **kwargs) -> Inputs:  # type: ignore
        raise NotImplementedError

    @property
    def resource_type(self):
        return self.__class__.__name__

    def outputs(self) -> T:  # type: ignore
        """
        Synchronously connect to the resource by fetching its outputs.
        """
        docker_client = DockerClient()
        containers = docker_client.list_containers(
            environment_name=launchflow.environment, resource_name=self.name
        )

        # If no containers match, it hasn't been created yet.
        # More than one matching should not happen by launchflow's doing.
        if len(containers) == 0:
            return self._outputs_type(password="password", ports={})  # type: ignore
        if len(containers) != 1:
            raise ValueError(f"Expected 1 container, got {len(containers)}")

        if containers[0].status != "running":
            raise exceptions.ResourceStopped(self.name)

        # Get the inputs dict, which is the same as the outputs for containers
        encoded_inputs = containers[0].labels.get("inputs", None)

        inputs_dict = base64_to_dict(encoded_inputs)
        return self._outputs_type(**inputs_dict, container_id=containers[0].id)  # type: ignore

    async def outputs_async(self) -> T:  # type: ignore
        """
        Asynchronously connect to the resource by fetching its outputs.
        """
        return self.outputs()
