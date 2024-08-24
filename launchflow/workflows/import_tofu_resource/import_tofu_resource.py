import tempfile

import yaml

from launchflow import exceptions
from launchflow.gcp_clients import write_to_gcs
from launchflow.workflows.commands.tf_commands import TFApplyCommand, TFImportCommand
from launchflow.workflows.import_tofu_resource.schemas import (
    ImportResourceTofuInputs,
    ImportResourceTofuOutputs,
)


async def import_tofu_resource(inputs: ImportResourceTofuInputs):
    state_prefix = inputs.launchflow_uri.tf_state_prefix(module=inputs.resource.product)

    tf_vars = {}
    if inputs.gcp_env_config:
        tf_vars.update(
            {
                "gcp_project_id": inputs.gcp_env_config.project_id,
                "gcp_region": inputs.gcp_env_config.default_region,
                "resource_id": inputs.resource_id,
                "artifact_bucket": inputs.gcp_env_config.artifact_bucket,
                "environment_service_account_email": inputs.gcp_env_config.service_account_email,
                **inputs.resource.inputs,  # type: ignore
            }
        )
    else:
        tf_vars.update(
            {
                "aws_region": inputs.aws_env_config.region,  # type: ignore
                "resource_id": inputs.resource_id,
                "artifact_bucket": inputs.aws_env_config.artifact_bucket,  # type: ignore
                "env_role_name": inputs.aws_env_config.iam_role_arn.split("/")[-1],  # type: ignore
                "vpc_id": inputs.aws_env_config.vpc_id,  # type: ignore
                "launchflow_environment": inputs.launchflow_uri.environment_name,
                "launchflow_project": inputs.launchflow_uri.project_name,
                **inputs.resource.inputs,  # type: ignore
            }
        )
    tf_apply_command = TFApplyCommand(
        tf_module_dir=f"resources/{inputs.resource.product}",
        backend=inputs.backend,
        tf_state_prefix=state_prefix,
        tf_vars=tf_vars,
        logs_file=inputs.logs_file,
        launchflow_state_url=inputs.launchflow_uri.launchflow_tofu_state_url(
            inputs.lock_id, module=inputs.resource.product
        ),
    )

    with tempfile.TemporaryDirectory() as tempdir:
        # First import everything that is needed for the resource
        for key, value in inputs.imports.items():
            tf_import_command = TFImportCommand(
                tf_module_dir=tf_apply_command.tf_module_dir,
                backend=tf_apply_command.backend,
                tf_state_prefix=tf_apply_command.tf_state_prefix,
                tf_vars=tf_vars,
                logs_file=inputs.logs_file,
                launchflow_state_url=tf_apply_command.launchflow_state_url,
                resource=key,
                resource_id=value,
                drop_logs=False,
            )
            await tf_import_command.run(tempdir)
        # Next run the apply command to create any artifacts we need
        output = await tf_apply_command.run(tempdir)
        # TODO: it would be nice if we could have some validation here
        output_key = f"resources/{inputs.launchflow_uri.resource_name}.yaml"
        yaml_data = yaml.safe_dump(output)
        if inputs.gcp_env_config is not None:
            await write_to_gcs(
                bucket=inputs.gcp_env_config.artifact_bucket,  # type: ignore
                prefix=output_key,
                data=yaml_data,
            )
        if inputs.aws_env_config is not None:
            try:
                import boto3
            except ImportError:
                raise exceptions.MissingAWSDependency()
            client = boto3.client("s3")
            client.put_object(
                Bucket=inputs.aws_env_config.artifact_bucket,  # type: ignore
                Key=output_key,
                Body=yaml_data,
            )

    return ImportResourceTofuOutputs(
        gcp_id=output.get("gcp_id"), aws_arn=output.get("aws_arn")
    )
