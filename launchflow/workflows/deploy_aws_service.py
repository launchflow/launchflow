import asyncio
import base64
import logging
import os
from typing import IO, List

from docker.errors import BuildError  # type: ignore

from launchflow import exceptions
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.workflows.utils import tar_source_in_memory


async def _upload_source_tarball_to_s3(
    source_tarball_s3_path: str,
    artifact_bucket: str,
    local_source_dir: str,
    build_ignore: List[str],
):
    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()

    def upload_async():
        source_tarball = tar_source_in_memory(local_source_dir, build_ignore)

        try:
            bucket = boto3.resource(
                "s3",
                # TODO: Explore the idea of a launchflow.auth module that fetches
                # default creds and passes them to boto3 (or throws a nice error)
            ).Bucket(artifact_bucket)
            bucket.upload_fileobj(source_tarball, source_tarball_s3_path)

        except Exception:
            raise exceptions.UploadSrcTarballFailed()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, upload_async)


def _get_build_status(client, build_id):
    response = client.batch_get_builds(ids=[build_id])
    if not response["builds"]:
        raise ValueError("No build found for the provided build ID.")
    build_status = response["builds"][0]["buildStatus"]
    return build_status


async def _poll_build_completion(client, build_id, poll_interval=10):
    """
    Polls the status of a build until it is completed or fails.

    :param client: Boto3 CodeBuild client
    :param build_id: ID of the build to poll
    :param poll_interval: Time in seconds between each poll
    """
    while True:
        build_status = _get_build_status(client, build_id)
        if build_status in ["SUCCEEDED"]:
            break
        elif build_status in ["FAILED", "FAULT", "TIMED_OUT", "STOPPED"]:
            raise ValueError(f"Build failed with status: {build_status}")
        else:
            await asyncio.sleep(poll_interval)  # Use asyncio.sleep for async waiting


async def _run_docker_aws_code_build(
    docker_repository: str,
    docker_image_tag: str,
    aws_account_id: str,
    aws_region: str,
    code_build_project_name: str,
    dockerfile_path: str,
    artifact_bucket: str,
    launchflow_project_name: str,
    launchflow_environment_name: str,
    launchflow_service_name: str,
    build_log_file: IO,
):
    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()

    client = boto3.client("codebuild", region_name=aws_region)

    response = client.start_build(
        projectName=code_build_project_name,
        sourceTypeOverride="S3",
        sourceLocationOverride=f"{artifact_bucket}/builds/{launchflow_project_name}/{launchflow_environment_name}/services/{launchflow_service_name}/",
        environmentVariablesOverride=[
            {
                "name": "IMAGE_TAG",
                "value": docker_image_tag,
                "type": "PLAINTEXT",
            },
            {
                "name": "DOCKERFILE_PATH",
                "value": dockerfile_path,
            },
            {
                "name": "BUILD_MODE",
                "value": "build",
                "type": "PLAINTEXT",
            },
        ],
    )

    build_id = response["build"]["id"]  # type: ignore
    build_url = f"https://{aws_region}.console.aws.amazon.com/codesuite/codebuild/{aws_account_id}/projects/{code_build_project_name}/build/{build_id}/?region={aws_region}"

    try:
        await _poll_build_completion(client, build_id)
    except Exception as e:
        build_log_file.write(
            f"Error running AWS CodeBuild: {e}\nSee remote build logs at: {build_url}"
        )
        raise e

    # Return the docker image name and build url
    return f"{docker_repository}:{docker_image_tag}"


def _write_build_logs(f: IO, log_stream):
    for chunk in log_stream:
        if "stream" in chunk:
            f.write(chunk["stream"])


# TODO: Look into cleaning up old images. I noticed my docker images were taking up a lot of space
# after running this workflow multiple times
# TODO: consider moving this to a common docker module and pass in creds
async def _build_docker_image_local(
    aws_region: str,
    docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    local_source_dir: str,
    dockerfile_path: str,
    build_log_file: IO,
):
    try:
        from docker import errors, from_env  # type: ignore
    except ImportError:
        raise exceptions.MissingDockerDependency()
    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()

    docker_client = from_env()
    latest_image_name = f"{docker_repository}:latest"
    tagged_image_name = f"{docker_repository}:{docker_image_tag}"
    # Authenticate with the docker registry
    ecr_client = boto3.client("ecr", region_name=aws_region)
    ecr_credentials = ecr_client.get_authorization_token()["authorizationData"][0]
    ecr_password = (
        base64.b64decode(ecr_credentials["authorizationToken"])  # type: ignore
        .replace(b"AWS:", b"")
        .decode()
    )
    docker_client.login(
        username="AWS",
        password=ecr_password,
        registry=docker_repository.replace("https://", ""),
    )

    # Pull the latest image from the registry to use as a cache
    try:
        docker_client.images.pull(latest_image_name)
        cache_from = [latest_image_name]
    except errors.NotFound:
        # NOTE: this happens on the first build
        cache_from = []

    # Build the docker image with the cache from the latest image
    loop = asyncio.get_event_loop()
    try:
        _, log_stream = await loop.run_in_executor(
            None,
            lambda: docker_client.images.build(
                path=os.path.dirname(local_source_dir),
                dockerfile=dockerfile_path,
                tag=tagged_image_name,
                cache_from=cache_from,
                # NOTE: this is required to build on mac
                platform="linux/amd64",
            ),
        )
        _write_build_logs(build_log_file, log_stream)
    except BuildError as e:
        _write_build_logs(build_log_file, e.build_log)
        raise e

    # Tag as latest
    docker_client.images.get(tagged_image_name).tag(latest_image_name)

    # Push the images to the registry
    docker_client.images.push(tagged_image_name)
    docker_client.images.push(latest_image_name)

    # Return the docker image name
    return tagged_image_name


async def promote_ecr_docker_image_on_code_build(
    source_env_region: str,
    source_docker_image: str,
    target_ecr_repository: str,
    target_code_build_project_name: str,
    target_aws_region: str,
    aws_account_id: str,
    launchflow_deployment_id: str,
):
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        raise exceptions.MissingAWSDependency()

    # Fetch the source ecr registry credentials to pass into the build
    source_ecr_client = boto3.client("ecr", region_name=source_env_region)
    source_ecr_credentials = source_ecr_client.get_authorization_token()[
        "authorizationData"
    ][0]
    source_ecr_password = (
        base64.b64decode(source_ecr_credentials["authorizationToken"])  # type: ignore
        .replace(b"AWS:", b"")
        .decode()
    )
    # Create the code build client
    code_build_client = boto3.client("codebuild", region_name=target_aws_region)

    split_image = source_docker_image.split(":")
    source_image_repo_name = split_image[0]
    source_image_tag = split_image[1]

    try:
        response = code_build_client.start_build(
            # NOTE: We override the source type since there's no source code to build for promotion
            sourceTypeOverride="NO_SOURCE",
            projectName=target_code_build_project_name,
            environmentVariablesOverride=[
                {
                    "name": "IMAGE_TAG",
                    "value": launchflow_deployment_id,
                    "type": "PLAINTEXT",
                },
                {
                    "name": "BUILD_MODE",
                    "value": "promotion",
                },
                {
                    "name": "SOURCE_ECR_PASSWORD",
                    "value": source_ecr_password,
                },
                {
                    "name": "SOURCE_ENV_IMAGE_REPO_NAME",
                    "value": source_image_repo_name,
                },
                {
                    "name": "SOURCE_ENV_IMAGE_TAG",
                    "value": source_image_tag,
                },
            ],
        )

        build_id = response["build"]["id"]  # type: ignore
        build_url = f"https://{target_aws_region}.console.aws.amazon.com/codesuite/codebuild/{aws_account_id}/projects/{target_code_build_project_name}/build/{build_id}/?region={target_aws_region}"

        await _poll_build_completion(code_build_client, build_id)

    except ClientError as e:
        logging.exception("Error running AWS CodeBuild")
        raise e

    # Return the docker image name and build url
    return f"{target_ecr_repository}:{launchflow_deployment_id}", build_url


async def build_ecr_docker_image_on_code_build(
    dockerfile_path: str,
    build_directory: str,
    build_ignore: List[str],
    build_log_file: IO,
    ecr_repository: str,
    code_build_project_name: str,
    launchflow_project_name: str,
    launchflow_environment_name: str,
    launchflow_service_name: str,
    launchflow_deployment_id: str,
    aws_environment_config: AWSEnvironmentConfig,
) -> str:
    source_tarball_s3_path = f"builds/{launchflow_project_name}/{launchflow_environment_name}/services/{launchflow_service_name}/source.tar.gz"
    # Step 1 - Upload the source tarball to S3
    await _upload_source_tarball_to_s3(
        source_tarball_s3_path=source_tarball_s3_path,
        artifact_bucket=aws_environment_config.artifact_bucket,  # type: ignore
        local_source_dir=build_directory,
        build_ignore=build_ignore,
    )

    # Step 2 - Build and push the docker image
    docker_image = await _run_docker_aws_code_build(
        docker_repository=ecr_repository,
        docker_image_tag=launchflow_deployment_id,
        aws_account_id=aws_environment_config.account_id,
        aws_region=aws_environment_config.region,
        code_build_project_name=code_build_project_name,
        dockerfile_path=dockerfile_path,
        artifact_bucket=aws_environment_config.artifact_bucket,  # type: ignore
        launchflow_project_name=launchflow_project_name,
        launchflow_environment_name=launchflow_environment_name,
        launchflow_service_name=launchflow_service_name,
        build_log_file=build_log_file,
    )

    return docker_image


async def build_ecr_docker_image_locally(
    dockerfile_path: str,
    build_directory: str,
    build_ignore: List[str],
    build_log_file: IO,
    ecr_repository: str,
    launchflow_service_name: str,
    launchflow_deployment_id: str,
    aws_environment_config: AWSEnvironmentConfig,
) -> str:
    del build_ignore  # TODO: Use this to ignore files while building the docker image

    # Step 1 - Build and push the docker image
    docker_image = await _build_docker_image_local(
        aws_region=aws_environment_config.region,
        docker_repository=ecr_repository,
        docker_image_name=launchflow_service_name,
        docker_image_tag=launchflow_deployment_id,
        local_source_dir=build_directory,
        dockerfile_path=dockerfile_path,
        build_log_file=build_log_file,
    )

    return docker_image
