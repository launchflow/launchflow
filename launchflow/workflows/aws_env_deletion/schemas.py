from typing import Optional

from pydantic import BaseModel

from launchflow.models.launchflow_uri import LaunchFlowURI


class AWSEnvironmentDeletionInputs(BaseModel):
    launchflow_uri: LaunchFlowURI
    aws_region: str
    artifact_bucket: Optional[str]
    lock_id: str
    logs_file: str


class AWSEnvironmentDeletionOutputs(BaseModel):
    success: bool
