import logging

from pydantic import BaseModel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from launchflow import exceptions
from launchflow.config import config
from launchflow.workflows.aws_env_creation.schemas import (
    AWSEnvironmentCreationInputs,
    AWSEnvironmentCreationOutputs,
)
from launchflow.workflows.commands.tf_commands import TFApplyCommand
from launchflow.workflows.utils import run_tofu, unique_resource_name_generator


class _AWSTofuOutputs(BaseModel):
    vpc_id: str
    role_arn: str
    success: bool


async def _create_artifact_bucket(
    project_name: str, environment_name: str, region: str
):
    try:
        import boto3
    except ImportError:
        # TODO: make this a better exception
        raise exceptions.MissingAWSDependency()
    s3_client = boto3.client("s3")
    bucket_name = f"{project_name.lower()}-{environment_name.lower()}-artifacts"
    for unique_bucket_name in unique_resource_name_generator(bucket_name):
        try:
            if region == "us-east-1":
                # NOTE: us-east-1 is a special case where you don't need to set the location constraint
                # https://github.com/boto/boto3/issues/125
                s3_client.create_bucket(Bucket=unique_bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=unique_bucket_name,
                    # NOTE: you must set this for buckets defined in regions other than us-east-1
                    # context: https://github.com/aws/aws-cli/issues/2603
                    CreateBucketConfiguration={"LocationConstraint": region},  # type: ignore
                )
            break
        except s3_client.exceptions.BucketAlreadyExists:
            continue
    s3_client.put_bucket_lifecycle_configuration(
        Bucket=unique_bucket_name,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "log-file-expiration",
                    # TODO: make this configurable
                    "Expiration": {"Days": 14},
                    "Filter": {"Prefix": "logs/"},
                    "Status": "Enabled",
                }
            ]
        },
    )
    return unique_bucket_name


async def _run_tofu(
    inputs: AWSEnvironmentCreationInputs, artifact_bucket: str
) -> _AWSTofuOutputs:
    command = TFApplyCommand(
        tf_module_dir="environments/aws",
        backend=config.launchflow_yaml.backend,
        tf_state_prefix=inputs.launchflow_uri.tf_state_prefix(),
        tf_vars={
            "aws_region": inputs.region,
            "launchflow_project": inputs.launchflow_uri.project_name,
            "launchflow_environment": inputs.launchflow_uri.environment_name,
            "aws_account_id": inputs.aws_account_id,
            "artifact_bucket_name": artifact_bucket,
        },
        logs_file=inputs.logs_file,
        launchflow_state_url=inputs.launchflow_uri.launchflow_tofu_state_url(
            lock_id=inputs.lock_id
        ),
    )
    tf_outputs = await run_tofu(command)
    return _AWSTofuOutputs(
        vpc_id=tf_outputs["vpc_id"],
        role_arn=tf_outputs["role_arn"],
        success=True,
    )


async def create_aws_environment(
    inputs: AWSEnvironmentCreationInputs,
) -> AWSEnvironmentCreationOutputs:
    artifact_bucket = None
    vpc_id = None
    role_arn = None
    success = True
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("["),
            TimeElapsedColumn(),
            TextColumn("]"),
        ) as progress:
            create_bucket = progress.add_task("Creating artifact bucket...", total=1)
            if inputs.artifact_bucket is None:
                artifact_bucket = await _create_artifact_bucket(
                    inputs.launchflow_uri.project_name,
                    inputs.launchflow_uri.environment_name,
                    inputs.region,
                )
                progress.console.print(
                    f"[green]✓ Artifact bucket: {artifact_bucket} successfully created[/green]"
                )
                progress.remove_task(create_bucket)
            else:
                artifact_bucket = inputs.artifact_bucket

            create_environment = progress.add_task("Creating environment...", total=1)
            outputs = await _run_tofu(inputs, artifact_bucket)
            progress.remove_task(create_environment)
            vpc_id = outputs.vpc_id
            role_arn = outputs.role_arn
    except Exception:
        logging.exception("Error creating AWS environment")
        success = False

    return AWSEnvironmentCreationOutputs(
        vpc_id=vpc_id,
        role_arn=role_arn,
        artifact_bucket=artifact_bucket,
        success=success,
    )
