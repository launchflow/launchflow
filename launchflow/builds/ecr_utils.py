import asyncio
import base64
from typing import List

from launchflow import exceptions
from launchflow.workflows.utils import tar_source_in_memory


def authenticate_with_ecr(aws_region: str, docker_repository: str, docker_client):
    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()

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


async def upload_source_tarball_to_s3(
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
            ).Bucket(artifact_bucket)
            bucket.upload_fileobj(source_tarball, source_tarball_s3_path)

        except Exception:
            raise exceptions.UploadSrcTarballFailed()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, upload_async)
