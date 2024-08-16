from dataclasses import dataclass
from typing import Any, Dict, Optional

from docker.models.containers import Container  # type: ignore

from launchflow.models.flow_state import ResourceState


@dataclass
class CreateResourceDockerInputs:
    resource: ResourceState
    image: str
    env_vars: Dict[str, str]
    command: str
    ports: Dict[str, int]
    logs_file: Optional[str]

    environment_name: str
    resource_inputs: Dict[str, Any]


@dataclass
class CreateResourceDockerOutputs:
    container: Container
    ports: Dict[str, int]


@dataclass
class DestroyResourceDockerInputs:
    container_id: str
    logs_file: Optional[str]
