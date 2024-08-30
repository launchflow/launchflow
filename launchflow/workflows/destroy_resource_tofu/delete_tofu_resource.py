from launchflow import exceptions
from launchflow.gcp_clients import get_storage_client
from launchflow.workflows.commands.tf_commands import TFDestroyCommand
from launchflow.workflows.destroy_resource_tofu.schemas import DestroyResourceTofuInputs
from launchflow.workflows.utils import run_tofu


async def delete_tofu_resource(inputs: DestroyResourceTofuInputs):
    # TODO: there's a bug in here we need to fix before rolling out this
    # If the initial create fails the inputs aren't recorded and the user is unable
    # to destroy the resource. This could happen if the user isn't logged in or something.
    # I think the fix is to just make sure the inputs are always recorded.
    state_prefix = inputs.launchflow_uri.tf_state_prefix(module=inputs.resource.product)
    tf_vars = inputs.resource.inputs or inputs.resource.attempted_inputs or {}
    module_dir = inputs.resource.product
    module_dir = f"resources/{inputs.resource.product}"
    if inputs.resource.product == "unknown":
        return
    # TODO: I don't like this hard coding but it works for now
    is_k8_resource = inputs.resource.product.startswith("kubernetes")
    if is_k8_resource:
        # K8s resource are a little special cause they don't have the additional cloud provider
        # specific configuration that other resources have. We only care about the inputs
        # that are stored on the resource.
        pass
    elif inputs.resource.cloud_provider == "gcp" and inputs.gcp_env_config is not None:
        tf_vars.update(
            {
                "gcp_project_id": inputs.gcp_env_config.project_id,
                "gcp_region": inputs.gcp_env_config.default_region,
                "artifact_bucket": inputs.gcp_env_config.artifact_bucket,
                "environment_service_account_email": inputs.gcp_env_config.service_account_email,
            }
        )
    elif inputs.resource.cloud_provider == "aws" and inputs.aws_env_config is not None:
        tf_vars.update(
            {
                "aws_account_id": inputs.aws_env_config.account_id,
                "aws_region": inputs.aws_env_config.region,
                "artifact_bucket": inputs.aws_env_config.artifact_bucket,
                "env_role_name": inputs.aws_env_config.iam_role_arn.split("/")[  # type: ignore
                    -1
                ],  # type: ignore
                "vpc_id": inputs.aws_env_config.vpc_id,
                "launchflow_project": inputs.launchflow_uri.project_name,
                "launchflow_environment": inputs.launchflow_uri.environment_name,
            }
        )

    tf_destroy_command = TFDestroyCommand(
        tf_module_dir=module_dir,
        backend=inputs.backend,
        tf_state_prefix=state_prefix,
        tf_vars=tf_vars,
        logs_file=inputs.logs_file,
        launchflow_state_url=inputs.launchflow_uri.launchflow_tofu_state_url(
            inputs.lock_id, module=inputs.resource.product
        ),
    )

    await run_tofu(tf_destroy_command)

    output_key = f"resources/{inputs.launchflow_uri.resource_name}.yaml"
    if inputs.gcp_env_config is not None:
        try:
            from google.api_core.exceptions import NotFound
        except ImportError:
            raise exceptions.MissingGCPDependency()
        try:
            client = get_storage_client()
            remote_bucket = client.bucket(inputs.gcp_env_config.artifact_bucket)
            remote_bucket.blob(output_key).delete()
        except NotFound:
            pass
    if inputs.aws_env_config is not None:
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()
        client = boto3.client("s3")
        client.delete_object(
            Bucket=inputs.aws_env_config.artifact_bucket,
            Key=output_key,
        )
    return
