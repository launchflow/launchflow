import asyncio
import base64
import logging
import os
import time
from typing import List, Tuple

from docker.errors import BuildError  # type: ignore

from launchflow import exceptions
from launchflow.aws.ecs_fargate import ECSFargate
from launchflow.aws.service import AWSDockerService, AWSService
from launchflow.config import config
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.flow_state import AWSEnvironmentConfig, ServiceState
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
):
    try:
        import boto3
        from botocore.exceptions import ClientError
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

    build_id = response["build"]["id"]
    build_url = f"https://{aws_region}.console.aws.amazon.com/codesuite/codebuild/{aws_account_id}/projects/{code_build_project_name}/build/{build_id}/?region={aws_region}"

    try:
        await _poll_build_completion(client, build_id)
    except ClientError as e:
        raise exceptions.ServiceBuildFailed(
            error_message=f"Error running AWS CodeBuild: {e}",
            build_logs_or_link=build_url,
        )

    # Return the docker image name and build url
    return f"{docker_repository}:{docker_image_tag}", build_url


def _write_build_logs(file_path: str, log_stream):
    with open(file_path, "w") as f:
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
    build_logs_file: str,
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
        base64.b64decode(ecr_credentials["authorizationToken"])
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
        _write_build_logs(build_logs_file, log_stream)
    except BuildError as e:
        _write_build_logs(build_logs_file, e.build_log)
        raise exceptions.ServiceBuildFailed(
            error_message=f"Error building docker image: {e}",
            build_logs_or_link=build_logs_file,
        )

    # Tag as latest
    docker_client.images.get(tagged_image_name).tag(latest_image_name)

    # Push the images to the registry
    docker_client.images.push(tagged_image_name)
    docker_client.images.push(latest_image_name)

    # Return the docker image name
    return tagged_image_name


async def _promote_docker_image(
    source_env_region: str,
    source_docker_image: str,
    docker_repository: str,
    docker_image_tag: str,
    aws_account_id: str,
    aws_region: str,
    code_build_project_name: str,
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
        base64.b64decode(source_ecr_credentials["authorizationToken"])
        .replace(b"AWS:", b"")
        .decode()
    )
    # Create the code build client
    code_build_client = boto3.client("codebuild", region_name=aws_region)

    split_image = source_docker_image.split(":")
    source_image_repo_name = split_image[0]
    source_image_tag = split_image[1]

    try:
        response = code_build_client.start_build(
            # NOTE: We override the source type since there's no source code to build for promotion
            sourceTypeOverride="NO_SOURCE",
            projectName=code_build_project_name,
            environmentVariablesOverride=[
                {
                    "name": "IMAGE_TAG",
                    "value": docker_image_tag,
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

        build_id = response["build"]["id"]
        build_url = f"https://{aws_region}.console.aws.amazon.com/codesuite/codebuild/{aws_account_id}/projects/{code_build_project_name}/build/{build_id}/?region={aws_region}"

        await _poll_build_completion(code_build_client, build_id)

    except ClientError as e:
        logging.exception("Error running AWS CodeBuild")
        raise e

    # Return the docker image name and build url
    return f"{docker_repository}:{docker_image_tag}", build_url


async def build_and_push_aws_service(
    aws_service: AWSService,
    service_manager: ServiceManager,
    aws_environment_config: AWSEnvironmentConfig,
    deployment_id: str,
    build_local: bool,
) -> Tuple[str, str]:
    if build_local:
        return await build_aws_service_locally(
            aws_service=aws_service,
            service_manager=service_manager,
            aws_environment_config=aws_environment_config,
            deployment_id=deployment_id,
        )
    return await build_docker_image_on_code_build(
        aws_service=aws_service,
        service_manager=service_manager,
        aws_environment_config=aws_environment_config,
        deployment_id=deployment_id,
    )


async def build_docker_image_on_code_build(
    aws_service: AWSDockerService,
    service_manager: ServiceManager,
    aws_environment_config: AWSEnvironmentConfig,
    deployment_id: str,
) -> Tuple[str, str]:
    full_yaml_path = os.path.dirname(
        os.path.abspath(config.launchflow_yaml.config_path)
    )
    local_source_dir = os.path.join(full_yaml_path, aws_service.build_directory)
    source_tarball_s3_path = f"builds/{service_manager.project_name}/{service_manager.environment_name}/services/{service_manager.service_name}/source.tar.gz"
    # Step 1 - Upload the source tarball to S3
    await _upload_source_tarball_to_s3(
        source_tarball_s3_path=source_tarball_s3_path,
        artifact_bucket=aws_environment_config.artifact_bucket,  # type: ignore
        local_source_dir=local_source_dir,
        build_ignore=aws_service.build_ignore,
    )

    service_outputs = aws_service.outputs()

    # Step 2 - Build and push the docker image
    docker_image, build_url = await _run_docker_aws_code_build(
        docker_repository=service_outputs.docker_repository,
        docker_image_tag=deployment_id,
        aws_account_id=aws_environment_config.account_id,
        aws_region=aws_environment_config.region,
        code_build_project_name=service_outputs.code_build_project_name,
        dockerfile_path=aws_service.dockerfile,
        artifact_bucket=aws_environment_config.artifact_bucket,  # type: ignore
        launchflow_project_name=service_manager.project_name,
        launchflow_environment_name=service_manager.environment_name,
        launchflow_service_name=service_manager.service_name,
    )

    return docker_image, build_url


async def build_aws_service_locally(
    aws_service: AWSDockerService,
    service_manager: ServiceManager,
    aws_environment_config: AWSEnvironmentConfig,
    deployment_id: str,
) -> Tuple[str, str]:
    full_yaml_path = os.path.dirname(
        os.path.abspath(config.launchflow_yaml.config_path)
    )
    local_source_dir = os.path.join(full_yaml_path, aws_service.build_directory)

    service_outputs = aws_service.outputs()

    base_logging_dir = "/tmp/launchflow"
    os.makedirs(base_logging_dir, exist_ok=True)
    build_logs_file = (
        f"{base_logging_dir}/{service_manager.service_name}-{int(time.time())}.log"
    )

    # Step 1 - Build and push the docker image
    docker_image = await _build_docker_image_local(
        aws_region=aws_environment_config.region,
        docker_repository=service_outputs.docker_repository,
        docker_image_name=service_manager.service_name,
        docker_image_tag=deployment_id,
        local_source_dir=local_source_dir,
        dockerfile_path=aws_service.dockerfile,
        build_logs_file=build_logs_file,
    )

    return docker_image, build_logs_file


async def release_docker_image_to_ecs_fargate(
    docker_image: str,
    service_manager: ServiceManager,
    aws_environment_config: AWSEnvironmentConfig,
    ecs_fargate_service: ECSFargate,
    deployment_id: str,
) -> str:
    try:
        import boto3
        from botocore.exceptions import WaiterError
    except ImportError:
        raise exceptions.MissingAWSDependency()

    ecs_client = boto3.client("ecs", region_name=aws_environment_config.region)
    cluster_name = ecs_fargate_service._ecs_cluster.resource_id
    service_name = ecs_fargate_service._ecs_fargate_service_container.resource_id

    alb_outputs = ecs_fargate_service._alb.outputs()

    task_definition_name = f"{service_name}-task"

    existing_task_def_response = ecs_client.describe_task_definition(
        taskDefinition=task_definition_name
    )
    new_task_definition = existing_task_def_response["taskDefinition"]
    # Update the Docker image reference in the task definition
    new_task_definition["containerDefinitions"][0]["image"] = docker_image
    # Remove the hello world command and entrypoint
    if "command" in new_task_definition["containerDefinitions"][0]:
        del new_task_definition["containerDefinitions"][0]["command"]
    if "entryPoint" in new_task_definition["containerDefinitions"][0]:
        del new_task_definition["containerDefinitions"][0]["entryPoint"]

    # Add the environment variables
    new_task_definition["containerDefinitions"][0]["environment"] = [
        {
            "name": "LAUNCHFLOW_ARTIFACT_BUCKET",
            "value": f"s3://{aws_environment_config.artifact_bucket}",
        },
        {"name": "LAUNCHFLOW_PROJECT", "value": service_manager.project_name},
        {"name": "LAUNCHFLOW_ENVIRONMENT", "value": service_manager.environment_name},
        {"name": "LAUNCHFLOW_CLOUD_PROVIDER", "value": "aws"},
        {"name": "LAUNCHFLOW_DEPLOYMENT_ID", "value": deployment_id},
    ]

    # Pulled from: https://stackoverflow.com/questions/69830579/aws-ecs-using-boto3-to-update-a-task-definition
    remove_args = [
        "compatibilities",
        "registeredAt",
        "registeredBy",
        "status",
        "revision",
        "taskDefinitionArn",
        "requiresAttributes",
    ]
    for arg in remove_args:
        new_task_definition.pop(arg)

    new_task_definition["tags"] = [
        {"key": "Project", "value": service_manager.project_name},
        {"key": "Environment", "value": service_manager.environment_name},
    ]
    reg_task_def_response = ecs_client.register_task_definition(**new_task_definition)

    ecs_client.update_service(
        cluster=cluster_name,
        service=service_name,
        taskDefinition=reg_task_def_response["taskDefinition"]["taskDefinitionArn"],
    )
    # This waiter will wait for the service to reach a steady state. It raises an error after 60 attempts.
    waiter = ecs_client.get_waiter("services_stable")
    try:
        waiter.wait(
            cluster=cluster_name,
            services=[service_name],
            WaiterConfig={"Delay": 15, "MaxAttempts": 60},
        )
    except WaiterError as e:
        # TODO: Raise a custom exception here
        # TODO: Add a check to see if the task is crash looping, and maybe rollback the task definition
        raise e

    return alb_outputs.alb_dns_name


# TODO: add a way to promote the docker image without code build
async def promote_aws_service_image(
    aws_service: AWSService,
    from_service_state: ServiceState,
    from_aws_environment_config: AWSEnvironmentConfig,
    to_aws_environment_config: AWSEnvironmentConfig,
    deployment_id: str,
    promote_local: bool,
) -> Tuple[str, str]:
    service_outputs = aws_service.outputs()

    # Step 1 - Promote the existing docker image
    if not promote_local:
        return await _promote_docker_image(
            source_env_region=from_aws_environment_config.region,
            # TODO: add validation around the docker image being set
            source_docker_image=from_service_state.docker_image,  # type: ignore
            docker_repository=service_outputs.docker_repository,
            docker_image_tag=deployment_id,
            aws_account_id=to_aws_environment_config.account_id,
            aws_region=to_aws_environment_config.region,
            code_build_project_name=service_outputs.code_build_project_name,
        )
    else:
        raise NotImplementedError(
            "Promoting local docker images is not yet supported for AWS services."
        )
