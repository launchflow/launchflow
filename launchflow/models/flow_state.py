import datetime
from typing import Any, Dict, List, Optional

# TODO: Move to dataclasses
from pydantic import BaseModel, Field

from launchflow.models.enums import (
    CloudProvider,
    EnvironmentStatus,
    EnvironmentType,
    ResourceStatus,
    ServiceStatus,
)


class _Entity(BaseModel):
    created_at: datetime.datetime
    updated_at: datetime.datetime


class GCPEnvironmentConfig(BaseModel):
    project_id: Optional[str]
    default_region: str
    default_zone: str
    service_account_email: Optional[str]
    artifact_bucket: Optional[str]
    vpc_connection_managed: bool = True


class AWSEnvironmentConfig(BaseModel):
    account_id: str
    region: str
    iam_role_arn: Optional[str]
    vpc_id: Optional[str]
    artifact_bucket: Optional[str]


# TODO: Added name to this, might as well add name to everything?
class ResourceState(_Entity):
    name: str
    cloud_provider: Optional[CloudProvider]
    product: str
    status: ResourceStatus
    gcp_id: Optional[str] = None
    aws_arn: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    depends_on: List[str] = Field(default_factory=list)
    # These are the inputs that were attempted to be used to create the resource
    # these will only be set if the resource is in a failed state
    attempted_inputs: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return self.model_dump(mode="json", exclude_defaults=True)


class ServiceState(_Entity):
    name: str
    cloud_provider: CloudProvider
    product: str
    status: ServiceStatus
    gcp_id: Optional[str] = None
    aws_arn: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    service_url: Optional[str] = None
    docker_image: Optional[str] = None  # TODO: mark this as deprecated somehow
    # TODO: Update all calling code to stop depending on docker_iamge and use
    # deployment_id to look it up instead
    deployment_id: Optional[str] = None

    def to_dict(self):
        return self.model_dump(mode="json", exclude_defaults=True)


# TODO: Maybe move env_name into the Environment model
class EnvironmentState(_Entity):
    environment_type: EnvironmentType
    gcp_config: Optional[GCPEnvironmentConfig] = None
    aws_config: Optional[AWSEnvironmentConfig] = None
    status: EnvironmentStatus = EnvironmentStatus.READY

    def to_dict(self):
        return self.model_dump(mode="json", exclude_defaults=True)


class ProjectState(_Entity):
    name: str

    def to_dict(self):
        return self.model_dump(mode="json")
