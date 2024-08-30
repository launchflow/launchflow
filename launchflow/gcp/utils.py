import logging
import os
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from google.auth.credentials import Credentials

from launchflow import exceptions
from launchflow.cache import cache
from launchflow.config import config
from launchflow.managers.environment_manager import EnvironmentManager

_ServiceAccountEmailMetadataKey = "instance/service-accounts/default/email"
_ServiceAccountTokenMetadataKey = "instance/service-accounts/default/token"


# Cloud Run automatically sets the K_SERVICE environment variable
# Docs: https://cloud.google.com/run/docs/container-contract#env-vars
def _is_running_on_cloud_run():
    """Check if running on Google Cloud Run."""
    return "K_SERVICE" in os.environ


# Cloud Run instances expose a metadata server to fetch info at runtime
# Docs: https://cloud.google.com/run/docs/reference/container-contract#metadata-server
def _get_cloud_run_metadata(metadata_key: str):
    """
    Get the metadata value from the Cloud Run instance metadata server.
    """
    metadata_server_url = "http://metadata.google.internal/computeMetadata/v1/"
    metadata_server_url += metadata_key

    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_server_url, headers=headers)
    if metadata_key == _ServiceAccountTokenMetadataKey:
        return response.json()
    return response.text


def _get_gcp_service_account_email_from_remote_sync(
    project_name: str, environment_name: str
):
    em = EnvironmentManager(
        project_name=project_name,
        environment_name=environment_name,
        backend=config.launchflow_yaml.backend,
    )
    env = em.load_environment_sync()
    gcp_config = env.gcp_config
    if gcp_config is None:
        raise exceptions.GCPConfigNotFound(environment_name)
    service_account = gcp_config.service_account_email
    if service_account is None:
        raise exceptions.GCPEnvironmentMissingServiceAccount(environment_name)
    return service_account


def _get_gcp_service_account_email_from_flowstate(
    project_name: Optional[str] = None,
    environment_name: Optional[str] = None,
):
    project_name = project_name or config.project
    environment_name = environment_name or config.environment
    if project_name is None or environment_name is None:
        raise exceptions.ProjectOrEnvironmentNotSet(project_name, environment_name)

    gcp_service_account_email = cache.get_gcp_service_account_email(
        project_name, environment_name
    )
    if gcp_service_account_email is not None:
        logging.debug(
            f"Using cached GCP service account email for {project_name}/{environment_name}"
        )
        return gcp_service_account_email

    logging.debug(
        f"Fetching GCP service account email for {project_name}/{environment_name}"
    )
    gcp_service_account_email = _get_gcp_service_account_email_from_remote_sync(
        project_name, environment_name
    )
    cache.set_gcp_service_account_email(
        project_name, environment_name, gcp_service_account_email
    )

    return gcp_service_account_email


def get_service_account_credentials(
    project_name: Optional[str] = None,
    environment_name: Optional[str] = None,
) -> "Credentials":
    """
    Get the GCP service account credentials for the specified project and environment.
    """
    try:
        from google.auth import default, impersonated_credentials
    except ImportError:
        raise exceptions.MissingGCPDependency()

    if _is_running_on_cloud_run():
        # If running on Cloud Run, fetch the service account from the metadata server
        gcp_service_account_email = _get_cloud_run_metadata(
            _ServiceAccountEmailMetadataKey
        )
    else:
        # If not on Cloud Run, fetch the GCP service account email from the FlowState
        gcp_service_account_email = _get_gcp_service_account_email_from_flowstate(
            project_name, environment_name
        )

    # Load the default credentials (from environment, compute engine, etc.)
    creds, _ = default()
    # Define the target service account to impersonate
    target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    target_credentials = impersonated_credentials.Credentials(
        source_credentials=creds,
        target_principal=gcp_service_account_email,
        target_scopes=target_scopes,
        lifetime=30 * 60,  # The maximum lifetime in seconds
    )

    return target_credentials
