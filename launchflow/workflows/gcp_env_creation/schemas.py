from dataclasses import dataclass
from typing import Optional

from launchflow.models.launchflow_uri import LaunchFlowURI


@dataclass
class GCPEnvironmentCreationInputs:
    launchflow_uri: LaunchFlowURI
    lock_id: str
    logs_file: str
    connect_launchflow_environment: bool = False
    gcp_project_id: Optional[str] = None
    environment_service_account_email: Optional[str] = None
    org_name: Optional[str] = None
    artifact_bucket: Optional[str] = None
    vpc_connection_managed: Optional[bool] = None


@dataclass
class GCPEnvironmentCreationOutputs:
    gcp_project_id: Optional[str]
    environment_service_account_email: Optional[str]
    artifact_bucket: Optional[str]
    success: bool
    vpc_connection_managed: bool
