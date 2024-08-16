import datetime
import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# TODO: figure out how to better parse enums so we can make these lowercase
class OperationStatus(enum.Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    WORKING = "WORKING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    def is_final(self):
        return self in [
            OperationStatus.SUCCESS,
            OperationStatus.FAILURE,
            OperationStatus.CANCELLED,
            OperationStatus.EXPIRED,
            OperationStatus.TIMEOUT,
            OperationStatus.INTERNAL_ERROR,
        ]

    def is_error(self):
        return self in [
            OperationStatus.FAILURE,
            OperationStatus.INTERNAL_ERROR,
            OperationStatus.TIMEOUT,
        ]

    def is_success(self):
        return self == OperationStatus.SUCCESS

    def is_canceled(self):
        return self == OperationStatus.CANCELLED


class OperationResponse(BaseModel):
    id: str
    status: OperationStatus
    status_message: Optional[str]
    project_name: str
    environment_name: Optional[str]
    build_url: Optional[str] = None


class ResourceResponse(BaseModel):
    name: str
    cloud_provider: str
    resource_product: str
    status: str
    status_message: Optional[str]
    create_args: Dict[str, Any]
    connection_bucket_path: Optional[str]
    gcp_id: Optional[str]
    aws_arn: Optional[str]

    def __str__(self) -> str:
        return f"Resource(name='{self.name}', resource_product='{self.resource_product}', status='{self.status}')"


class ServiceResponse(BaseModel):
    name: str
    status: str
    status_message: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    cloud_provider: str
    service_product: str
    create_args: Dict[str, Any]
    service_url: Optional[str]

    def __str__(self) -> str:
        return f"Service(name='{self.name}', service_product='{self.service_product}', status='{self.status}')"


class ProjectResponse(BaseModel):
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    configured_cloud_providers: List[str]
    status: str
    status_message: str


class GCPEnvironmentConfigResponse(BaseModel):
    created_at: datetime.datetime
    updated_at: datetime.datetime
    gcp_project_id: str
    gcp_service_account_email: str
    default_gcp_region: str
    default_gcp_zone: str
    artifact_bucket: str


class AWSEnvironmentConfigResponse(BaseModel):
    created_at: datetime.datetime
    updated_at: datetime.datetime
    aws_region: str
    aws_iam_role_arn: str
    aws_vpc_id: str
    artifact_bucket: str


class EnvironmentType(enum.Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class EnvironmentResponse(BaseModel):
    name: str
    environment_type: EnvironmentType
    created_at: datetime.datetime
    updated_at: datetime.datetime
    gcp_config: Optional[GCPEnvironmentConfigResponse] = None
    aws_config: Optional[AWSEnvironmentConfigResponse] = None
    status: str
    status_message: str
    resources: Dict[str, ResourceResponse] = {}


class AccountResponse(BaseModel):
    id: str


class AccountConnectionResponse(BaseModel):
    gcp_service_account_email: str
    aws_external_role_id: str
    aws_account_id: str
    aws_role_name: str
