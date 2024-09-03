from typing import Any

import yaml

from launchflow import exceptions
from launchflow.aws.resource import AWSResource
from launchflow.backend import Backend
from launchflow.gcp.resource import GCPResource
from launchflow.gcp_clients import write_to_gcs
from launchflow.kubernetes.resource import KubernetesResource
from launchflow.models.flow_state import EnvironmentState
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.resource import _to_output_type
from launchflow.tofu import TofuResource
from launchflow.workflows.apply_resource_tofu.schemas import ApplyResourceTofuOutputs
from launchflow.workflows.commands.tf_commands import TFApplyCommand
from launchflow.workflows.utils import run_tofu


async def update_gcp_tofu_resource_outputs(
    artifact_bucket: str,
    resource_name: str,
    outputs: Any,  # TODO: Fix this type
):
    # TODO: it would be nice if we could have some validation here
    output_key = f"resources/{resource_name}.yaml"
    yaml_data = yaml.safe_dump(outputs)

    await write_to_gcs(
        bucket=artifact_bucket,
        prefix=output_key,
        data=yaml_data,
    )


async def update_aws_tofu_resource_outputs(
    artifact_bucket: str,
    resource_name: str,
    outputs: Any,  # TODO: Fix this type
):
    # TODO: it would be nice if we could have some validation here
    output_key = f"resources/{resource_name}.yaml"
    yaml_data = yaml.safe_dump(outputs)

    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()
    client = boto3.client("s3")
    client.put_object(
        Bucket=artifact_bucket,
        Key=output_key,
        Body=yaml_data,
    )


async def create_tofu_resource(
    tofu_resource: TofuResource,
    environment_state: EnvironmentState,
    backend: Backend,
    launchflow_uri: LaunchFlowURI,
    lock_id: str,
    logs_file: str,
):
    materialized_inputs = tofu_resource.execute_inputs(environment_state)

    state_prefix = launchflow_uri.tf_state_prefix(module=tofu_resource.tf_module)
    lf_state_url = launchflow_uri.launchflow_tofu_state_url(
        lock_id=lock_id, module=tofu_resource.tf_module
    )

    tf_vars = {}
    if (
        isinstance(tofu_resource, GCPResource)
        and environment_state.gcp_config is not None
    ):
        tf_vars.update(
            {
                "gcp_project_id": environment_state.gcp_config.project_id,
                "gcp_region": environment_state.gcp_config.default_region,
                "artifact_bucket": environment_state.gcp_config.artifact_bucket,
                "environment_service_account_email": environment_state.gcp_config.service_account_email,
                **materialized_inputs.to_dict(),
            }
        )
    elif (
        isinstance(tofu_resource, AWSResource)
        and environment_state.aws_config is not None
    ):
        tf_vars.update(
            {
                "aws_account_id": environment_state.aws_config.account_id,
                "aws_region": environment_state.aws_config.region,
                "artifact_bucket": environment_state.aws_config.artifact_bucket,
                "env_role_name": environment_state.aws_config.iam_role_arn.split("/")[  # type: ignore
                    -1
                ],  # type: ignore
                "vpc_id": environment_state.aws_config.vpc_id,
                "launchflow_project": launchflow_uri.project_name,
                "launchflow_environment": launchflow_uri.environment_name,
                **materialized_inputs.to_dict(),
            }
        )
    elif isinstance(tofu_resource, KubernetesResource):
        tf_vars.update(
            {
                # TODO: add common vars here
                **materialized_inputs.to_dict(),
            }
        )

    tf_apply_command = TFApplyCommand(
        tf_module_dir=f"resources/{tofu_resource.tf_module}",
        backend=backend,  # type: ignore
        tf_state_prefix=state_prefix,
        tf_vars=tf_vars,
        logs_file=logs_file,
        launchflow_state_url=lf_state_url,
    )

    tf_outputs = await run_tofu(tf_apply_command)
    try:
        # Validate that the outputs can be parsed. This shouldn't happen
        # and if it does there is likely a bug, but we don't want to
        # tell the user we succeeded if we potentially won't be able to
        # read the outputs.
        _to_output_type(tf_outputs, tofu_resource._outputs_type)
    except Exception as e:
        raise exceptions.InvalidOutputForResource(tofu_resource.name, e) from e

    if environment_state.gcp_config is not None:
        await update_gcp_tofu_resource_outputs(
            artifact_bucket=environment_state.gcp_config.artifact_bucket,  # type: ignore
            resource_name=launchflow_uri.resource_name,  # type: ignore
            outputs=tf_outputs,
        )
    if environment_state.aws_config is not None:
        await update_aws_tofu_resource_outputs(
            artifact_bucket=environment_state.aws_config.artifact_bucket,  # type: ignore
            resource_name=launchflow_uri.resource_name,  # type: ignore
            outputs=tf_outputs,
        )

    return ApplyResourceTofuOutputs(
        gcp_id=tf_outputs.get("gcp_id"), aws_arn=tf_outputs.get("aws_arn")
    )
