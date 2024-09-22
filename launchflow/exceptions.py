from datetime import timedelta
from typing import Any, List, Optional

from launchflow.utils import get_failure_text


class ComingSoon(Exception):
    def __init__(self, issue_number: int) -> None:
        super().__init__(
            f"""ComingSoon!

This feature is coming soon or may have been added in a newer version of LaunchFlow.
                
See https://github.com/launchflow/launchflow/issues/{issue_number} for more information.
"""
        )


class LaunchFlowException(Exception):
    def pretty_print(self):
        print(self)


class LaunchFlowRequestFailure(LaunchFlowException):
    def __init__(self, response) -> None:
        super().__init__(get_failure_text(response))
        self.status_code = response.status_code


class NoLaunchFlowCredentials(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No launchflow credentials found. Run `lf login` to authenticate with LaunchFlow Cloud."
        )


class InvalidBackend(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidProjectNameInYaml(Exception):
    def __init__(self, project_name: str, reason: str) -> None:
        super().__init__(
            f"Invalid project name in launchflow.yaml: {project_name}\nReason: {reason}"
        )


class InvalidDefaultEnvironmentInYaml(Exception):
    def __init__(self, environment_name: str, reason: str) -> None:
        super().__init__(
            f"Invalid default environment in launchflow.yaml: {environment_name}\nReason: {reason}"
        )


class InvalidGCPProjectName(Exception):
    def __init__(self, project_name: str) -> None:
        super().__init__(
            f"The generated GCP project name contains invalid characters: {project_name}. GCP project names can only contain lowercase letters, numbers, and hyphens.\n\nThis name is generated by combining the launchflow project name from launchflow.yaml with the current launchflow environment name. Please ensure that both the project and environment names meet the naming requirements."
        )


class CannotDefaultMultipleAccounts(Exception):
    def __init__(self, account_ids: List[str]) -> None:
        super().__init__(
            f"The lf://default backend cannot be used when you have multiple accounts. Please use a specific account id (e.g. lf://{account_ids[0]}).\n\nYou have access tothe following accounts: {account_ids}\n"
        )


class NoEnvironmentsFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("No environments found.")


# TODO: Move "potential fix" messsages into the server.
# Server should return a json payload with a message per client type, i.e.
# {status: 409, message: "Conflict...", fix: {"cli": "Run this command..."}}
# Use details to return the fix payload:
# details = {message: "...", fix: {"cli": "Run this command..."}}
class ResourceOutputsNotFound(Exception):
    def __init__(self, resource_name: str) -> None:
        super().__init__(
            f"Outputs for resource '{resource_name}' not found. "
            f"\n\nPotential Fix:\nRun `lf create` it.\n\n"
        )


class ServiceOutputsNotFound(Exception):
    def __init__(self, service_name: str) -> None:
        super().__init__(
            f"Outputs for service '{service_name}' not found. "
            f"\n\nPotential Fix:\nRun `lf deploy` to deploy it.\n\n"
        )


class ServiceOutputsMissingField(Exception):
    def __init__(self, service_name: str, field_name: str) -> None:
        super().__init__(
            f"Outputs for service '{service_name}' are missing an expected field: {field_name}"
            f"\n\nThis is an unexpected state - please email team@launchflow.com if the error persists.\n\n"
        )


class ResourceStopped(Exception):
    def __init__(self, resource_name: str) -> None:
        super().__init__(
            f"Resource '{resource_name}' is not running."
            f"\n\nPotential Fix:\nRun `launchflow create` to start it.\n\n"
        )


class PermissionCannotReadOutputs(Exception):
    def __init__(self, resource_name: str, bucket_path: str) -> None:
        super().__init__(
            f"Permission denied reading outputs for resource '{resource_name}' please ensure you have access to read the bucket: {bucket_path}"
        )


class ForbiddenOutputs(Exception):
    def __init__(self, bucket_url) -> None:
        super().__init__(
            f"Failed to read outputs from bucket. Please ensure you have access at: {bucket_url}"
        )


class ProjectOrEnvironmentNotSet(Exception):
    def __init__(self, project: Optional[str], environment: Optional[str]) -> None:
        super().__init__(
            f"Project or environment name not set. Set the project and environment names using "
            f"launchflow.yaml or the environment variables LAUNCHFLOW_PROJECT and LAUNCHFLOW_ENVIRONMENT. "
            f"\n\nCurrent project: {project}\nCurrent environment: {environment}\n\n"
        )


class ResourceProductMismatch(Exception):
    def __init__(self, resource: Any, existing_product: str, new_product: str) -> None:
        super().__init__(
            f"Resource '{resource}' already exists with a different product. "
            f"Existing product: {existing_product}, new product: {new_product}."
        )


class ServiceProductMismatch(Exception):
    def __init__(self, service: Any, existing_product: str, new_product: str) -> None:
        super().__init__(
            f"Service '{service}' already exists with a different product. "
            f"Existing product: {existing_product}, new product: {new_product}."
        )


class ServiceMissingDeploymentId(Exception):
    def __init__(self, service_name: str) -> None:
        super().__init__(
            f"Service '{service_name}' is missing a deployment id. Please run `lf deploy {service_name}` to deploy it before promoting."
        )


class GCPConfigNotFound(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"GCP configuration not found for environment '{environment_name}'. "
            "This environment is most likely an AWS environment."
        )


class AWSConfigNotFound(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"AWS configuration not found for environment '{environment_name}'. "
            "This environment hasn't been configured for AWS yet."
        )


class ProjectNotFound(Exception):
    def __init__(self, project_name: str) -> None:
        super().__init__(f"Project '{project_name}' not found.")


class EnvironmentNotFound(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' not found. Create the environment with `lf environments create {environment_name}`."
        )


class EnvironmentCreationFailed(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(f"Failed to create environment '{environment_name}'.")


class EnvironmentInFailedCreateState(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' is in a failed create state. You can retry the create operation with `lf environments create {environment_name}`."
        )


class LaunchFlowProjectNotFound(Exception):
    def __init__(self, project_name: str) -> None:
        super().__init__(
            f"LaunchFlow project '{project_name}' not found. Create the project with `lf projects create {project_name}`."
        )


class ServiceNotFound(Exception):
    def __init__(self, service_name: str) -> None:
        super().__init__(f"Service '{service_name}' not found.")


class ResourceNotFound(Exception):
    def __init__(self, resource_name: str) -> None:
        super().__init__(f"Resource '{resource_name}' not found.")


class MultipleBillingAccounts(Exception):
    def __init__(self) -> None:
        super().__init__(
            "You have access to multiple billing accounts. Please run again without the -y flag to select a billing account."
        )


class NoBillingAccountAccess(Exception):
    def __init__(self) -> None:
        super().__init__(
            "You do not have access to a billing account. Ensure you have access to a billing account and try again.",
        )


class NoBillingAccountSelected(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No billing account selected. Exiting.",
        )


class NoOrgs(Exception):
    def __init__(self) -> None:
        super().__init__(
            "You do not have access to any organizations. Ensure you have access to an organiztaion and try again."
        )


class TofuOutputFailure(Exception):
    def __init__(self) -> None:
        super().__init__("Tofu output failed")


class TofuApplyFailure(Exception):
    def __init__(self) -> None:
        super().__init__("Tofu apply failed.")


class TofuInitFailure(Exception):
    def __init__(self) -> None:
        super().__init__("Tofu init failed")


class TofuImportFailure(Exception):
    def __init__(self) -> None:
        super().__init__("Tofu import failed")


class TofuDestroyFailure(Exception):
    def __init__(self) -> None:
        super().__init__("Tofu destroy failed")


class EntityLocked(Exception):
    def __init__(self, entity: str) -> None:
        super().__init__(
            f"Entity is locked (`{entity}`). Wait for the operation to complete."
        )


class EntityNotLocked(Exception):
    def __init__(self, entity: str) -> None:
        super().__init__(f"Entity is not locked (`{entity}`).")


class LockNotAcquired(Exception):
    def __init__(self) -> None:
        super().__init__("Lock not acquired.")


class LockNotFound(Exception):
    def __init__(self, entity: str) -> None:
        super().__init__(f"Lock not found on `{entity}`.")


class LockMismatch(Exception):
    def __init__(self, entity: str) -> None:
        super().__init__(
            f"Cannot unlock an entity (`{entity}`) that you do not hold the lock for."
        )


class MissingGCPDependency(Exception):
    def __init__(self) -> None:
        super().__init__(
            "GCP dependencies are not installed. Install them with: `pip install launchflow[gcp]`"
        )


class MissingAWSDependency(Exception):
    def __init__(self) -> None:
        super().__init__(
            "AWS dependencies are not installed. Install them with: `pip install launchflow[aws]`"
        )


class MissingDockerDependency(Exception):
    def __init__(self, details: str = "") -> None:
        msg = "Docker is not installed."
        if details:
            msg += f" {details}"
        super().__init__(msg)


class LaunchFlowYamlNotFound(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No launchflow.yaml could be found, please ensure you are in the correct directory."
        )


class LaunchFlowBackendRequired(Exception):
    def __init__(self) -> None:
        super().__init__("A LaunchFlow backend is required.")


# TODO: Add a link to documentation for setting up AWS credentials.
class NoAWSCredentialsFound(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No AWS credentials found. Please ensure you have AWS credentials set up in your environment."
        )


class ExistingEnvironmentDifferentEnvironmentType(Exception):
    def __init__(self, environment_name: str, environment_type: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' already exists with a different environment type '{environment_type}'."
        )


class ExistingEnvironmentDifferentCloudProvider(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' already exists with a different cloud provider type."
        )


class ExistingEnvironmentDifferentGCPProject(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' already exists with a different GCP project."
        )


class ExistingEnvironmentDifferentGCPBucket(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' already exists with a different GCS artifact bucket."
        )


class ExistingEnvironmentDifferentGCPServiceAccount(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' already exists with a different environment service account email."
        )


class GCPEnvironmentMissingServiceAccount(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' does not have a service account set up."
        )


class GCSObjectNotFound(Exception):
    def __init__(self, bucket: str, prefix: str) -> None:
        super().__init__(
            f"GCS object not found in bucket '{bucket}' with prefix '{prefix}'."
        )


class ProjectStateNotFound(Exception):
    def __init__(self) -> None:
        super().__init__("Project state not found.")


class UploadSrcTarballFailed(Exception):
    def __init__(self) -> None:
        super().__init__("Failed to upload source tar file")


class OpenTofuInstallFailure(Exception):
    def __init__(self) -> None:
        super().__init__("OpenTofu install failed.")


class ServiceStateMismatch(Exception):
    def __init__(self, service: Any) -> None:
        super().__init__(
            f"Service {service} was updated before the plan was locked, please rerun the command to deploy the service."
        )


class ResourceStateMismatch(Exception):
    def __init__(self, resource: Any) -> None:
        super().__init__(
            f"Resource {resource} was updated before the plan was locked, please rerun the command to create the resource."
        )


class InvalidResourceName(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class DuplicateResourceProductMismatch(Exception):
    def __init__(
        self, resource_name: str, existing_product: str, new_product: str
    ) -> None:
        super().__init__(
            f"Resource `{resource_name}` was defined twice as different resource types. Existing type: {existing_product}, new type: {new_product}."
        )


class DuplicateServiceProductMismatch(Exception):
    def __init__(
        self, service_name: str, existing_product: str, new_product: str
    ) -> None:
        super().__init__(
            f"Service `{service_name}` was defined twice as different service types. Existing type: {existing_product}, new type: {new_product}."
        )


class EnvironmentNotEmpty(Exception):
    def __init__(self, environment_name: str) -> None:
        super().__init__(
            f"Environment '{environment_name}' is not empty.\n"
            "You can list / delete all resources and services with the following command:"
            "\n\n"
            f"    $ lf destroy {environment_name}"
            "\n\n"
        )


class ProjectNotEmpty(Exception):
    def __init__(self, project_name: str) -> None:
        super().__init__(
            f"Project '{project_name}' still has environments. Please delete them first.\n"
            "You can list the environments with the following command:"
            "\n\n"
            f"    $ lf environments list --project {project_name}"
            "\n\n"
            "You can delete an environment with the following command:"
            "\n\n"
            f"    $ lf environments delete <environment_name> --project {project_name}"
            "\n\n"
        )


class PlanAlreadyLocked(Exception):
    def __init__(self, plan: Any) -> None:
        super().__init__(f"Plan '{plan}' is already locked.")


class FailedToLockPlans(Exception):
    def __init__(self, exceptions_list: List[Exception]) -> None:
        super().__init__(f"Failed to lock one or more plans: {exceptions_list}")


class GCPDockerPullFailed(Exception):
    def __init__(self, service_account_email: Optional[str], docker_image: str) -> None:
        split_image = docker_image.split("/")
        gcp_project_id = split_image[1]
        split_image[0].split(".")[0]
        repository = split_image[2]
        split_image[3].split(":")[0]
        console_url = (
            f"https://console.cloud.google.com/artifacts/docker/{gcp_project_id}"
        )
        msg = f"Failed to pull docker image from repository '{docker_image}'."
        if service_account_email:
            msg += f"\n\tUsing service account '{service_account_email}'."
            msg += f"\n\tGrant the service account reader access to `{repository}` as {console_url}"
        else:
            msg += ".\n\tMake sure you have access to the repository."
        super().__init__(msg)


class NoAWSRegionError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No AWS region found. Set the AWS region with `aws configure` or by setting the AWS_REGION environment variable."
        )


class NoAWSRegionEvironmentCreationError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No AWS region found. Set the AWS region with `aws configure` or by setting the AWS_REGION environment variable. Or run without the -y flag to be prompted to choose one"
        )


class FileNotFoundError(Exception):
    def __init__(self, file_path: str) -> None:
        super().__init__(f"File: `{file_path}` was not found.")


class PermissionDeniedFileRead(Exception):
    def __init__(self, file_path: str) -> None:
        super().__init__(f"Failed to read file: `{file_path}`. Permission")


class InvalidOutputForResource(Exception):
    def __init__(self, resource_name: str, error: Exception) -> None:
        super().__init__(
            f"Invalid outputs for resource '{resource_name}'. This is likely a bug with the current version. Reach out to `team@launchflow.com` and trying running `lf create` again. Error: {error}"
        )


class GCEServiceNotHealthyTimeout(Exception):
    def __init__(self, timeout: timedelta) -> None:
        super().__init__(
            f"Service was not healthy after {timeout.total_seconds() / 60} minutes."
        )
