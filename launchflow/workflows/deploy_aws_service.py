import asyncio
import base64
import logging

from launchflow import exceptions


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
