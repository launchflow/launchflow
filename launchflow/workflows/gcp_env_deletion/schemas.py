from dataclasses import dataclass

from launchflow.models.flow_state import EnvironmentState
from launchflow.models.launchflow_uri import LaunchFlowURI


@dataclass
class GCPEnvironmentDeletionInputs:
    launchflow_uri: LaunchFlowURI
    environment_state: EnvironmentState
