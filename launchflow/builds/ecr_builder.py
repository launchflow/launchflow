import asyncio
import base64
from typing import IO, List, Literal, Optional

from docker.client import from_env
from docker.errors import BuildError  # type: ignore

from docker import errors
from launchflow import exceptions
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.workflows.utils import tar_source_in_memory


def _write_build_logs(f: IO, log_stream):
    for chunk in log_stream:
        if "stream" in chunk:
            f.write(chunk["stream"])


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


class ECRDockerBuilder:
    def __init__(
        self,
        build_directory: str,
        build_ignore: List[str],
        build_log_file: IO,
        ecr_repository: str,
        launchflow_project_name: str,
        launchflow_environment_name: str,
        launchflow_service_name: str,
        launchflow_deployment_id: str,
        aws_environment_config: AWSEnvironmentConfig,
    ):
        self.build_directory = build_directory
        self.build_ignore = build_ignore
        self.build_log_file = build_log_file
        self.ecr_repository = ecr_repository
        self.launchflow_project_name = launchflow_project_name
        self.launchflow_environment_name = launchflow_environment_name
        self.launchflow_service_name = launchflow_service_name
        self.launchflow_deployment_id = launchflow_deployment_id
        self.aws_environment_config = aws_environment_config
        self.docker_client = from_env()
        self.latest_image_name = f"{self.ecr_repository}:latest"
        self.tagged_image_name = (
            f"{self.ecr_repository}:{self.launchflow_deployment_id}"
        )

    async def build_with_nixpacks_local(self):
        self._authenticate_with_ecr()
        # Build the image
        # TODO: should we run in the build directory or pass the build directory to nixpacks
        # this probably depends on whether you can configure multiple builds with a nixpacks.toml
        cmd = f"nixpacks build . --name {self.tagged_image_name} --platform=linux/amd64"
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=self.build_log_file,
            stderr=self.build_log_file,
            cwd=self.build_directory,
        )
        await proc.communicate()

        if proc.returncode != 0:
            raise exceptions.NixPacksBuildFailed(
                service_name=self.launchflow_service_name,
            )

        self._tag_and_push()

        return self.tagged_image_name

    async def build_with_nixpacks_remote(self, codebuild_project_name: str):
        return await self._run_aws_code_build(
            code_build_project_name=codebuild_project_name,
            build_type="nixpacks",
        )

    async def build_with_docker_local(self, dockerfile_path: str):
        self._authenticate_with_ecr()

        # Pull the latest image from the registry to use as a cache
        try:
            self.docker_client.images.pull(self.latest_image_name)
            cache_from = [self.latest_image_name]
        except errors.NotFound:
            # NOTE: this happens on the first build
            cache_from = []
        # Build the docker image with the cache from the latest image
        loop = asyncio.get_event_loop()
        try:
            _, log_stream = await loop.run_in_executor(
                None,
                lambda: self.docker_client.images.build(
                    path=self.build_directory,
                    dockerfile=dockerfile_path,
                    tag=self.tagged_image_name,
                    cache_from=cache_from,
                    # NOTE: this is required to build on mac
                    platform="linux/amd64",
                ),
            )
            _write_build_logs(self.build_log_file, log_stream)
        except BuildError as e:
            _write_build_logs(self.build_log_file, e.build_log)
            raise e
        self._tag_and_push()
        return self.tagged_image_name

    async def build_with_docker_remote(
        self, dockerfile_path: str, codebuild_project_name: str
    ):
        return await self._run_aws_code_build(
            code_build_project_name=codebuild_project_name,
            build_type="docker",
            dockerfile_path=dockerfile_path,
        )

    def _authenticate_with_ecr(self):
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()

        ecr_client = boto3.client("ecr", region_name=self.aws_environment_config.region)
        ecr_credentials = ecr_client.get_authorization_token()["authorizationData"][0]
        ecr_password = (
            base64.b64decode(ecr_credentials["authorizationToken"])  # type: ignore
            .replace(b"AWS:", b"")
            .decode()
        )
        self.docker_client.login(
            username="AWS",
            password=ecr_password,
            registry=self.ecr_repository.replace("https://", ""),
        )

    async def _upload_source_tarball_to_s3(self):
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()
        source_tarball_s3_path = f"builds/{self.launchflow_project_name}/{self.launchflow_environment_name}/services/{self.launchflow_service_name}/source.tar.gz"

        def upload_async():
            source_tarball = tar_source_in_memory(
                self.build_directory, self.build_ignore
            )

            try:
                bucket = boto3.resource(
                    "s3",
                ).Bucket(
                    self.aws_environment_config.artifact_bucket
                )  # type: ignore
                bucket.upload_fileobj(source_tarball, source_tarball_s3_path)

            except Exception as e:
                raise exceptions.UploadSrcTarballFailed() from e

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, upload_async)

    def _tag_and_push(self):
        self.docker_client.images.get(self.tagged_image_name).tag(
            self.latest_image_name
        )

        # Push the image
        self.docker_client.images.push(self.tagged_image_name)
        self.docker_client.images.push(self.latest_image_name)

    async def _run_aws_code_build(
        self,
        code_build_project_name: str,
        build_type: Literal["nixpacks", "docker"],
        dockerfile_path: Optional[str] = None,
    ):
        aws_region = self.aws_environment_config.region
        await self._upload_source_tarball_to_s3()
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()

        client = boto3.client("codebuild", region_name=aws_region)

        env_vars = [
            {
                "name": "IMAGE_TAG",
                "value": self.launchflow_deployment_id,
                "type": "PLAINTEXT",
            },
            {"name": "BUILD_TYPE", "value": build_type, "type": "PLAINTEXT"},
            {"name": "BUILD_MODE", "value": "build", "type": "PLAINTEXT"},
        ]
        if build_type == "docker":
            if dockerfile_path is None:
                raise ValueError(
                    "dockerfile path must be provided for building docker images"
                )
            env_vars.append(
                {
                    "name": "DOCKERFILE_PATH",
                    "value": dockerfile_path,
                }
            )

        response = client.start_build(
            projectName=code_build_project_name,
            sourceTypeOverride="S3",
            sourceLocationOverride=f"{self.aws_environment_config.artifact_bucket}/builds/{self.launchflow_project_name}/{self.launchflow_environment_name}/services/{self.launchflow_service_name}/",
            environmentVariablesOverride=env_vars,  # type: ignore
        )

        build_id = response["build"]["id"]  # type: ignore
        build_url = f"https://{aws_region}.console.aws.amazon.com/codesuite/codebuild/{self.aws_environment_config.account_id}/projects/{code_build_project_name}/build/{build_id}/?region={aws_region}"

        try:
            await _poll_build_completion(client, build_id)
        except Exception as e:
            self.build_log_file.write(
                f"Error running AWS CodeBuild: {e}\nSee remote build logs at: {build_url}"
            )
            raise e

        return f"{self.ecr_repository}:{self.launchflow_deployment_id}"
