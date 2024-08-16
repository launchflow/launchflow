import logging
import os
import random
import socket
from typing import Dict

from docker.models.containers import Container  # type: ignore

from launchflow.clients.docker_client import DockerClient, PortAlreadyAllocatedError
from launchflow.config import config
from launchflow.managers.docker_resource_manager import dict_to_base64
from launchflow.utils import logging_output, redirect_stdout_stderr
from launchflow.workflows.manage_docker.schemas import (
    CreateResourceDockerInputs,
    CreateResourceDockerOutputs,
    DestroyResourceDockerInputs,
)

MAX_ASSIGNABLE_PORT = 65535


def _container_unique_name(resource_name: str, environment_name: str) -> str:
    """
    Generates a unique name for a container in an environment.

    Args:
    - `resource_name`: The name of the resource.
    - `environment_name`: The name of the environment.

    Returns:
    The unique name for the container.
    """
    return f"{environment_name}-{resource_name}"


def _start_container_with_retries(
    inputs: CreateResourceDockerInputs,
    volumes: Dict[str, Dict[str, str]],
    max_retries: int = 10,
) -> Container:
    """
    Utility to start a container with retries.
    Assumes the container does not already exist.

    Args:
    - `inputs`: The inputs for the create operation.
    - `volumes`: The volumes to mount in the container.
    - `max_retries`: The maximum number of retries to attempt.

    Returns:
    The container object.
    """
    docker_client = DockerClient()
    remaining_retries = max_retries + 1

    ports = inputs.ports
    if None in ports.values():
        ports = {k: find_open_port() for k in ports}

    container = None
    inputs.resource_inputs["ports"] = ports
    additional_labels = {
        "environment": inputs.environment_name,
        "resource": inputs.resource.name,
        "inputs": dict_to_base64(inputs.resource_inputs),
    }
    while remaining_retries > 0:
        try:
            container = docker_client.start_container(
                name=_container_unique_name(
                    inputs.resource.name, inputs.environment_name
                ),
                image=inputs.image,
                env_vars=inputs.env_vars,
                command=inputs.command,
                ports=ports,
                volumes=volumes,
                additional_labels=additional_labels,
            )
            break
        except PortAlreadyAllocatedError:
            remaining_retries -= 1
            logging.warning(
                "Reassigning the ports due to a port allocated error and retrying!"
            )
            ports = {k: find_open_port() for k in ports}
            inputs.resource_inputs["ports"] = ports
            additional_labels["inputs"] = dict_to_base64(inputs.resource_inputs)
            docker_client.remove_container(inputs.resource.name)

    if container is None:
        raise RuntimeError(
            f"Failed to find an open port to start docker container after {max_retries + 1} tries."
        )

    inputs.ports = ports

    return container


def find_open_port(start_port: int = 5432, max_checks=20) -> int:
    """Find an open port starting from a given port.

    Chooses a port randomly from a range to make retries easy -- if two resources try to use
    the same port and collide, they have a tiny probability of colliding again the next time.

    Args:
    - `start_port`: The port to start searching from.
    - `max_checks`: The number of ports to check before giving up.

    Returns:
    - The port number found.
    """
    search_range = (start_port, MAX_ASSIGNABLE_PORT)
    for _ in range(max_checks):
        port = random.randint(*search_range)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue

    raise RuntimeError(
        f"Could not find an open port in range {search_range} after {max_checks} checks."
    )


async def create_docker_resource(
    inputs: CreateResourceDockerInputs,
) -> CreateResourceDockerOutputs:
    """
    Creates a docker resource by starting a container.

    Args:
    - `inputs`: The inputs for the create operation.

    Returns:
    The outputs of the the create operation.
    """
    with logging_output(inputs.logs_file) as f:
        with redirect_stdout_stderr(f):
            launchflow_yaml_path = config.launchflow_yaml.config_path
            dot_launchflow_path = os.path.join(
                os.path.dirname(launchflow_yaml_path), ".launchflow"
            )
            resource_volume_path = os.path.join(
                dot_launchflow_path, "resources", inputs.resource.name, "volume"
            )
            os.makedirs(resource_volume_path, exist_ok=True)

            # TODO: add support for individual resources to set more than just home
            # (e.g. /var/lib/postgresql/data)
            volumes = {resource_volume_path: {"bind": "/home", "mode": "rw"}}

            container = _start_container_with_retries(inputs, volumes)

            return CreateResourceDockerOutputs(container, inputs.ports)


async def replace_docker_resource(
    inputs: CreateResourceDockerInputs,
) -> CreateResourceDockerOutputs:
    """
    Replaces a docker cresource by stopping and removing the old docker containerand starting a new one.
    Note: this function ends up called on "update" operations, which may require a replacement, but
          also may not (e.g. if the container is just exited). Since it's not expensive to stop, remove,
          and start a container, we do not check for this case.

    Args:
    - `inputs`: The inputs for the create operation.

    Returns:
    The outputs of the the create operation.
    """
    docker_client = DockerClient()
    with logging_output(inputs.logs_file) as f:
        with redirect_stdout_stderr(f):
            container_name = _container_unique_name(
                inputs.resource.name, inputs.environment_name
            )
            docker_client.stop_container(container_name)
            docker_client.remove_container(container_name)
            return await create_docker_resource(inputs)


async def destroy_docker_resource(inputs: DestroyResourceDockerInputs) -> None:
    """
    Destroys a docker resource by removing the container.

    Args:
    - `inputs`: The inputs for the destroy operation.
    """
    with logging_output(inputs.logs_file) as f:
        with redirect_stdout_stderr(f):
            DockerClient().remove_container(inputs.container_id, force=True)
