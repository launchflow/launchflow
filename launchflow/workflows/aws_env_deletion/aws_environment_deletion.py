from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from launchflow import exceptions
from launchflow.config import config
from launchflow.workflows.aws_env_deletion.schemas import AWSEnvironmentDeletionInputs
from launchflow.workflows.commands.tf_commands import TFDestroyCommand
from launchflow.workflows.utils import run_tofu


def _delete_artifact_bucket(bucket_name: str):
    try:
        import boto3
        import botocore
    except ImportError:
        raise exceptions.MissingAWSDependency()
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    try:
        # First delete all objects in the bucket
        bucket.objects.all().delete()
        # Then delete the bucket
        bucket.delete()
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            return
        raise


async def _run_tofu(inputs: AWSEnvironmentDeletionInputs):
    command = TFDestroyCommand(
        tf_module_dir="empty/aws_empty",
        backend=config.launchflow_yaml.backend,
        tf_state_prefix=inputs.launchflow_uri.tf_state_prefix(),
        tf_vars={
            "aws_region": inputs.aws_region,
        },
        launchflow_state_url=inputs.launchflow_uri.launchflow_tofu_state_url(
            lock_id=inputs.lock_id
        ),
        logs_file=inputs.logs_file,
    )
    return await run_tofu(command)


async def delete_aws_environment(inputs: AWSEnvironmentDeletionInputs):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn("["),
        TimeElapsedColumn(),
        TextColumn("]"),
    ) as progress:
        if inputs.artifact_bucket is not None:
            artifact_bucket = progress.add_task("Deleting artifact bucket...", total=1)
            _delete_artifact_bucket(inputs.artifact_bucket)
            progress.remove_task(artifact_bucket)
            progress.console.print(
                f"[green]✓ Artifact bucket: `{inputs.artifact_bucket}` successfully deleted[/green]"
            )

        delete_environment = progress.add_task("Deleting environment...", total=1)
        result = await _run_tofu(inputs)
        progress.remove_task(delete_environment)
        progress.console.print(
            f"[green]✓ AWS Environment: `{inputs.launchflow_uri.environment_name}` successfully deleted[/green]"
        )
        return result
