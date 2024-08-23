import re

from launchflow import exceptions

# TODO: Make sure these match the remote validation rules
MIN_PROJECT_NAME_LENGTH = 3
MAX_PROJECT_NAME_LENGTH = 63
PROJECT_PATTERN = r"^[a-zA-Z0-9-]+$"

MAX_ENVIRONMENT_NAME_LENGTH = 15
MIN_ENVIRONMENT_NAME_LENGTH = 1
ENVIRONMENT_PATTERN = r"^[a-z0-9-]+$"
RESERVED_ENVIRONMENT_NAMES = {
    "gcp",
    "aws",
    "azure",
    "local",
    "base",
    "default",
    "nix",
}


MIN_RESOURCE_NAME_LENGTH = 3
MAX_RESOURCE_NAME_LENGTH = 63
RESOURCE_PATTERN = r"^[a-zA-Z0-9-_\.]+$"


MIN_SERVICE_NAME_LENGTH = 3
MAX_SERVICE_NAME_LENGTH = 63
SERVICE_PATTERN = r"^[a-zA-Z0-9-_]+$"


def validate_project_name(project_name: str):
    if len(project_name) > MAX_PROJECT_NAME_LENGTH:
        raise ValueError(
            f"Project name must be at most {MAX_PROJECT_NAME_LENGTH} characters long"
        )
    if len(project_name) < MIN_PROJECT_NAME_LENGTH:
        raise ValueError(
            f"Project name must be at least {MIN_PROJECT_NAME_LENGTH} characters long"
        )
    if " " in project_name:
        raise ValueError("Project name cannot contain spaces")
    if "_" in project_name:
        raise ValueError("Project name cannot contain underscores")
    if not re.match(PROJECT_PATTERN, project_name):
        raise ValueError("Project name can only contain letters, numbers, and hyphens")


def validate_environment_name(environment_name: str):
    if len(environment_name) > MAX_ENVIRONMENT_NAME_LENGTH:
        raise ValueError(
            f"Environment name must be at most {MAX_ENVIRONMENT_NAME_LENGTH} characters long"
        )
    if len(environment_name) < MIN_ENVIRONMENT_NAME_LENGTH:
        raise ValueError(
            f"Environment name must be at least {MIN_ENVIRONMENT_NAME_LENGTH} characters long"
        )
    if " " in environment_name:
        raise ValueError("Environment name cannot contain spaces")
    if "_" in environment_name:
        raise ValueError("Environment name cannot contain underscores")
    if not re.match(ENVIRONMENT_PATTERN, environment_name):
        raise ValueError(
            "Environment name can only contain lowercase letters, numbers, and hyphens"
        )
    if environment_name in RESERVED_ENVIRONMENT_NAMES:
        raise ValueError(f"Environment name is reserved: {environment_name}")


def validate_resource_name(resource_name: str):
    if len(resource_name) > MAX_RESOURCE_NAME_LENGTH:
        raise exceptions.InvalidResourceName(
            f"Resource name must be at most {MAX_RESOURCE_NAME_LENGTH} characters long"
        )
    if len(resource_name) < MIN_RESOURCE_NAME_LENGTH:
        raise exceptions.InvalidResourceName(
            f"Resource name must be at least {MIN_RESOURCE_NAME_LENGTH} characters long"
        )
    if " " in resource_name:
        raise exceptions.InvalidResourceName("Resource name cannot contain spaces")
    if not re.match(RESOURCE_PATTERN, resource_name):
        raise exceptions.InvalidResourceName(
            f"Resource name must match pattern {RESOURCE_PATTERN}"
        )


def validate_service_name(service_name: str):
    if len(service_name) > MAX_SERVICE_NAME_LENGTH:
        raise ValueError(
            f"Service name must be at most {MAX_SERVICE_NAME_LENGTH} characters long"
        )
    if len(service_name) < MIN_SERVICE_NAME_LENGTH:
        raise ValueError(
            f"Service name must be at least {MIN_SERVICE_NAME_LENGTH} characters long"
        )
    if " " in service_name:
        raise ValueError("Service name cannot contain spaces")
    if not re.match(SERVICE_PATTERN, service_name):
        raise exceptions.InvalidResourceName(
            f"Service name must match pattern {SERVICE_PATTERN}"
        )
