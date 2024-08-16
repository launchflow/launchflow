from dataclasses import dataclass
from typing import Optional, Union

from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    GCPEnvironmentConfig,
    ResourceState,
)
from launchflow.models.launchflow_uri import LaunchFlowURI


@dataclass
class DestroyResourceTofuInputs:
    launchflow_uri: LaunchFlowURI
    backend: Union[LocalBackend, GCSBackend, LaunchFlowBackend]
    gcp_env_config: Optional[GCPEnvironmentConfig]
    aws_env_config: Optional[AWSEnvironmentConfig]
    # NOTE: This is the new state to commit not the current state
    resource: ResourceState
    lock_id: str
    logs_file: Optional[str]
