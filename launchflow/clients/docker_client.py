import logging
from functools import cache
from typing import Any, Dict, List, Optional

from docker.errors import (  # type: ignore
    APIError,
    DockerException,
    ImageNotFound,
    NotFound,
)
from docker.models.containers import Container  # type: ignore
from docker.models.images import Image  # type: ignore

import docker


class PortAlreadyAllocatedError(Exception):
    def __init__(self, message):
        super().__init__(message)


@cache
def docker_service_available():
    try:
        docker.from_env()
        return True
    # TODO: Link to LF docs when we're erroring out for this. Might be nice to have a check_docker_available that raises
    # instead to link from one place.
    except DockerException:
        return False


class DockerClient:
    """
    Client to abstract common docker operations.
    """

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logging.error(f"An error occurred when trying to connect to Docker: {e}")
            logging.error(
                "This error usually occurs when Docker is not running or installed.\n"
                "You can install Docker Engine from https://docs.docker.com/engine/install/\n"
            )

    def get_container(self, name_or_id: str) -> Optional[Container]:
        """
        Get a Docker container by name or id.

        Args:
        - `name_or_id`: The name or id of the container.

        Returns:
        - The container object if it exists, or None otherwise.
        """
        try:
            container = self.client.containers.get(name_or_id)
            logging.info(f"Container {name_or_id} found.")
            return container
        except NotFound:
            logging.warning(f"No container with name/id {name_or_id} found.")
            return None
        except APIError as e:
            logging.error(
                f"Server returned error when trying to get container {name_or_id}: {e}"
            )
            return None

    def list_containers(
        self,
        environment_name: Optional[str] = None,
        resource_name: Optional[str] = None,
    ) -> List[Container]:
        """
        List all containers in an environment.

        Args:
        - `environment_name`: The name of the environment to filter on.
        - `resource_name`: The name of the resource to filter by to filter on.

        Returns:
        - A list of container objects.
        """
        filter_labels = ["launchflow_managed=true"]
        if environment_name is not None:
            filter_labels.append(f"environment={environment_name}")
        if resource_name is not None:
            filter_labels.append(f"resource={resource_name}")

        return self.client.containers.list(
            filters={
                "label": filter_labels,
            },
            all=True,
        )

    def start_container(
        self,
        name: str,
        image: str,
        env_vars: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        additional_labels: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Optional[Container]:
        """
        Start a Docker container from an image with a given name, environment variables, ports, and volumes.

        Args:
        - `name`: The name of the container.
        - `image`: The image to use for the container.
        - `env_vars`: A dictionary of environment variables to set in the container.
        - `command`: The command to run in the container.
        - `ports`: A dictionary of ports to expose in the container.
        - `volumes`: A dictionary of volumes to mount in the container.
        - `additional_labels`: A dictionary of labels to add to the container.

        Returns:
        - The container object if it was started successfully, or None otherwise.
        """
        try:
            logging.info(
                f"Attempting to start container '{name}' using image '{image}'."
            )

            labels = {
                "launchflow_managed": "true",
            }
            if additional_labels is not None:
                labels.update(additional_labels)

            container = self.client.containers.run(
                image,
                name=name,
                detach=True,
                environment=env_vars,
                command=command,
                ports=ports,
                volumes=volumes,
                labels=labels,
                **kwargs,
            )
            logging.info(f"Container '{name}' started successfully.")
            return container
        except ImageNotFound:
            logging.warning(f"Image '{image}' not found. Attempting to pull image.")
            self.pull_image(image)
            return self.start_container(name, image, env_vars, ports, volumes, **kwargs)  # type: ignore
        except APIError as e:
            logging.error(
                f"Server returned error when trying to start container '{name}': {e}"
            )

            # If the port is already in use, raise a custom exception to trigger a retry
            if "port is already allocated" in (error_message := str(e.explanation)):
                raise PortAlreadyAllocatedError(message=error_message) from e
            return None

    def stop_container(self, name_or_id: str) -> None:
        """
        Stop a Docker container by name or id.

        Args:
        - `name_or_id`: The name or id of the container.
        """
        try:
            container = self.get_container(name_or_id)
            if container:
                logging.info(f"Stopping container '{name_or_id}'.")
                container.stop()
                logging.info(f"Container '{name_or_id}' stopped successfully.")
        except NotFound:
            logging.warning(f"No container with name '{name_or_id}' to stop.")
        except APIError as e:
            logging.error(
                f"Server returned error when trying to stop container '{name_or_id}': {e}"
            )

    def remove_container(self, name_or_id: str, force: bool = False) -> None:
        """
        Remove a Docker container by name or id. Can be forced to remove running containers.

        Args:
        - `name_or_id`: The name or id of the container.
        - `force`: Passed to the underlying docker client.
        """
        try:
            container = self.get_container(name_or_id)
            if container:
                logging.info(f"Removing container '{name_or_id}'.")
                container.remove(force=force)
                logging.info(f"Container '{name_or_id}' removed successfully.")
        except NotFound:
            logging.warning(f"No container with name '{name_or_id}' to remove.")
        except APIError as e:
            logging.error(
                f"Server returned error when trying to remove container '{name_or_id}': {e}"
            )

    def pull_image(self, image: str) -> Optional[Image]:
        """
        Pull a Docker image by name.
        """
        try:
            pulled_image = self.client.images.pull(image)
            logging.info(f"Image '{image}' pulled successfully.")
            return pulled_image
        except APIError as e:
            logging.error(
                f"Server returned error when trying to pull image '{image}': {e}"
            )
            return None

    def build_and_push_image(self, config):
        """
        Build and push a Docker image according to the provided config.
        This function is not fully implemented as it requires additional config details.
        """
        logging.warning("The build_and_push_image method is not yet implemented.")
        pass
