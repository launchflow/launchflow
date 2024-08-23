# TODO: we probably have utils to use for this
import base64
from typing import Any, Dict, Optional, Tuple, Type

import yaml

from launchflow import exceptions
from launchflow.backend import DockerBackend
from launchflow.clients.docker_client import DockerClient
from launchflow.locks import DockerLock, Lock, LockOperation
from launchflow.managers.base import BaseManager
from launchflow.models.enums import ResourceProduct, ResourceStatus
from launchflow.models.flow_state import ResourceState


# TODO Unify with the encoding stuff in launchflow_tmp
def dict_to_base64(dictionary: Dict[Any, Any]) -> str:
    """Encode a dictionary to base64 string."""
    yaml_str = yaml.dump(dictionary)
    yaml_bytes = yaml_str.encode("utf-8")
    base64_str = base64.b64encode(yaml_bytes).decode("utf-8")
    return base64_str


def base64_to_dict(base64_str):
    """Decode a base64 string to a dictionary."""
    yaml_bytes = base64.b64decode(base64_str)
    yaml_str = yaml_bytes.decode("utf-8")
    dictionary = yaml.safe_load(yaml_str)
    return dictionary


# TODO: need to add tests to this file once it is all working


class DockerResourceManager(BaseManager):
    def __init__(
        self,
        project_name: str,
        environment_name: str,
        resource_name: str,
    ) -> None:
        super().__init__(DockerBackend())  # type: ignore
        self.project_name = project_name
        self.environment_name = environment_name
        self.resource_name = resource_name

        self._docker_client = DockerClient()

    # Write a reduce function to allow pickling without the docker client
    def __reduce__(self) -> Tuple[Type["DockerResourceManager"], Tuple[str, str, str]]:
        return (
            self.__class__,
            (self.project_name, self.environment_name, self.resource_name),
        )

    def get_running_container_id(self) -> Optional[str]:
        """
        Get the container id of the resource's running container if it exists.

        Returns:
        The container id if it exists, or None otherwise.
        """
        containers = self._docker_client.list_containers(
            environment_name=self.environment_name, resource_name=self.resource_name
        )

        if len(containers) == 0:
            return None
        if len(containers) > 1:
            raise Exception("More than one container found")

        return containers[0].id

    async def load_resource(self) -> ResourceState:
        containers = self._docker_client.list_containers(
            environment_name=self.environment_name, resource_name=self.resource_name
        )

        if len(containers) == 0:
            raise exceptions.ResourceNotFound(self.resource_name)
        if len(containers) > 1:
            raise ValueError("Expected to find 1 container, but got multiple")

        container = containers[0]
        inputs_encoded = container.labels.get("inputs", None)

        # Update failed status triggers a resource re-create
        return ResourceState(
            name=self.resource_name,
            product=ResourceProduct.LOCAL_DOCKER.value,
            cloud_provider=None,
            created_at=container.attrs["Created"],
            updated_at=container.attrs["Created"],
            status=(
                ResourceStatus.READY
                if container.status == "running"
                else ResourceStatus.UPDATE_FAILED
            ),
            inputs=base64_to_dict(inputs_encoded) if inputs_encoded else None,
            depends_on=[],
        )

    async def save_resource(self, resource: ResourceState, lock_id: str):
        # The state gets saved in the resource flow when the container is created, nothing to do here
        pass

    async def delete_resource(self, lock_id: str):
        # The state gets deleted in the resource flow when the container is deleted, nothing to do here
        pass

    async def lock_resource(self, operation: LockOperation) -> Lock:
        # No locking needed, nothing to do here
        return DockerLock(operation=operation)
