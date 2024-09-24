import tempfile
import unittest
from unittest import mock
from unittest.mock import patch

from docker.errors import BuildError

from launchflow.builds.ecr_builder import ECRDockerBuilder
from launchflow.exceptions import NixPacksBuildFailed
from launchflow.models.flow_state import AWSEnvironmentConfig


class ECRBuilderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.build_directory = "mock_build_directory"
        self.build_ignore = ["ignore_me"]
        self.ecr_repository = "mock_ecr_repository"
        self.launchflow_project_name = "mock_project"
        self.launchflow_environment_name = "mock_environment"
        self.launchflow_service_name = "mock_service"
        self.launchflow_deployment_id = "mock_deployment_id"
        self.aws_environment_config = AWSEnvironmentConfig(
            account_id="mock_account_id",
            region="mock_region",
            artifact_bucket="mock_bucket",
            iam_role_arn="mock_iam_role_arn",
            vpc_id="mock_vpc_id",
        )
        self.temp_output = tempfile.mkstemp()
        self.temp_output_handler = open(self.temp_output[1], "w")

    def tearDown(self) -> None:
        self.temp_output_handler.close()

    @patch("launchflow.builds.ecr_builder.ECRDockerBuilder._authenticate_with_ecr")
    @patch("asyncio.create_subprocess_shell")
    @patch("launchflow.builds.ecr_builder.from_env")
    async def test_build_with_nixpacks_local_success(
        self,
        docker_mock: mock.MagicMock,
        mock_async_subproc: mock.MagicMock,
        mock_authenticate_ecr: mock.MagicMock,
    ):
        # Setup mocks
        process_mock = mock.AsyncMock()

        async def communicate_mock():
            return ("output", "error")

        process_mock.coummunicate.side_effect = communicate_mock
        process_mock.returncode = 0
        mock_async_subproc.return_value = process_mock

        # Setting up the builder instance
        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        # Execute the build method
        result = await builder.build_with_nixpacks_local()

        # Verification
        mock_async_subproc.assert_called_once_with(
            cmd="nixpacks build . --name mock_ecr_repository:mock_deployment_id --platform=linux/amd64",
            stdout=self.temp_output_handler,
            stderr=self.temp_output_handler,
            cwd=self.build_directory,
        )
        self.assertEqual("mock_ecr_repository:mock_deployment_id", result)

        push_mock: mock.MagicMock = docker_mock.return_value.images.push
        self.assertEqual(2, push_mock.call_count)
        push_mock.assert_has_calls(
            [
                mock.call("mock_ecr_repository:mock_deployment_id"),
                mock.call("mock_ecr_repository:latest"),
            ]
        )

    @patch("launchflow.builds.ecr_builder.ECRDockerBuilder._authenticate_with_ecr")
    @patch("asyncio.create_subprocess_shell")
    @patch("launchflow.builds.ecr_builder.from_env")
    async def test_build_with_nixpacks_local_failure(
        self,
        docker_mock: mock.MagicMock,
        mock_async_subproc: mock.MagicMock,
        mock_authenticate_ecr: mock.MagicMock,
    ):
        # Setup mocks
        process_mock = mock.AsyncMock()

        async def communicate_mock():
            return ("output", "error")

        process_mock.coummunicate.side_effect = communicate_mock
        process_mock.returncode = 2
        mock_async_subproc.return_value = process_mock

        # Setting up the builder instance
        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )
        with self.assertRaises(NixPacksBuildFailed):
            # Execute the build method
            await builder.build_with_nixpacks_local()

        # Verification
        mock_async_subproc.assert_called_once_with(
            cmd="nixpacks build . --name mock_ecr_repository:mock_deployment_id --platform=linux/amd64",
            stdout=self.temp_output_handler,
            stderr=self.temp_output_handler,
            cwd=self.build_directory,
        )

    @patch("boto3.client")
    @patch("boto3.resource")
    async def test_build_with_nixpacks_remote_success(
        self, mock_boto3_resource: mock.MagicMock, mock_boto3_client: mock.MagicMock
    ):
        # Setup mock for AWS boto3 client
        mock_codebuild = mock.MagicMock()
        mock_codebuild.start_build.return_value = {"build": {"id": "test-build-id"}}
        mock_codebuild.batch_get_builds.return_value = {
            "builds": [{"buildStatus": "SUCCEEDED"}]
        }
        mock_s3 = mock.MagicMock()
        mock_bucket = mock.MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        mock_boto3_client.return_value = mock_codebuild
        mock_boto3_resource.return_value = mock_s3

        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        result = await builder.build_with_nixpacks_remote("test-codebuild-project-name")

        # Validation
        expected_image_name = f"{self.ecr_repository}:{self.launchflow_deployment_id}"
        self.assertEqual(expected_image_name, result)

        mock_boto3_client.assert_any_call(
            "codebuild", region_name=self.aws_environment_config.region
        )

        mock_codebuild.start_build.assert_called_once_with(
            projectName="test-codebuild-project-name",
            sourceTypeOverride="S3",
            sourceLocationOverride="mock_bucket/builds/mock_project/mock_environment/services/mock_service/",
            environmentVariablesOverride=[
                {
                    "name": "IMAGE_TAG",
                    "value": "mock_deployment_id",
                    "type": "PLAINTEXT",
                },
                {"name": "BUILD_TYPE", "value": "nixpacks", "type": "PLAINTEXT"},
                {"name": "BUILD_MODE", "value": "build", "type": "PLAINTEXT"},
            ],
        )
        mock_bucket.upload_fileobj.assert_called_once()

    @patch("boto3.client")
    @patch("boto3.resource")
    async def test_build_with_nixpacks_remote_failure(
        self, mock_boto3_resource: mock.MagicMock, mock_boto3_client: mock.MagicMock
    ):
        # Setup mock for AWS boto3 client
        mock_codebuild = mock.MagicMock()
        mock_codebuild.start_build.return_value = {"build": {"id": "test-build-id"}}
        mock_codebuild.batch_get_builds.return_value = {
            "builds": [{"buildStatus": "FAILED"}]
        }
        mock_s3 = mock.MagicMock()
        mock_bucket = mock.MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        mock_boto3_client.return_value = mock_codebuild
        mock_boto3_resource.return_value = mock_s3

        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        with self.assertRaises(ValueError):
            await builder.build_with_nixpacks_remote("test-codebuild-project-name")

    @patch("launchflow.builds.ecr_builder.ECRDockerBuilder._authenticate_with_ecr")
    @patch("launchflow.builds.ecr_builder.from_env")
    async def test_build_with_docker_local_success(
        self, docker_mock: mock.MagicMock, mock_authenticate_ecr: mock.MagicMock
    ):
        # Mock Docker API client
        docker_api_mock = mock.MagicMock()
        docker_mock.return_value = docker_api_mock

        image_mock = mock.MagicMock()
        docker_api_mock.images.build.return_value = (image_mock, iter(["mock_log"]))
        docker_api_mock.images.push.return_value = iter(["push_log"])

        # Setting up the builder instance
        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        # Execute the build method
        result = await builder.build_with_docker_local("Dockerfile")

        # Verification
        docker_api_mock.images.build.assert_called_once_with(
            path=self.build_directory,
            dockerfile="Dockerfile",
            tag=f"{self.ecr_repository}:{self.launchflow_deployment_id}",
            cache_from=["mock_ecr_repository:latest"],
            platform="linux/amd64",
        )
        self.assertEqual(
            f"{self.ecr_repository}:{self.launchflow_deployment_id}", result
        )

        push_calls = [
            mock.call(f"{self.ecr_repository}:{self.launchflow_deployment_id}"),
            mock.call(f"{self.ecr_repository}:latest"),
        ]
        docker_api_mock.images.push.assert_has_calls(push_calls, any_order=True)

    @patch("launchflow.builds.ecr_builder.ECRDockerBuilder._authenticate_with_ecr")
    @patch("launchflow.builds.ecr_builder.from_env")
    async def test_build_with_docker_local_failure(
        self, docker_mock: mock.MagicMock, mock_authenticate_ecr: mock.MagicMock
    ):
        # Mock Docker API client
        docker_api_mock = mock.MagicMock()
        docker_mock.return_value = docker_api_mock

        # Simulate BuildError during image build
        docker_api_mock.images.build.side_effect = BuildError(
            reason="failed",
            build_log=[],  # type: ignore
        )

        # Setting up the builder instance
        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        with self.assertRaises(BuildError):
            # Execute the build method
            await builder.build_with_docker_local("Dockerfile")

        # Verification
        docker_api_mock.images.build.assert_called_once_with(
            path=self.build_directory,
            dockerfile="Dockerfile",
            tag=f"{self.ecr_repository}:{self.launchflow_deployment_id}",
            cache_from=["mock_ecr_repository:latest"],
            platform="linux/amd64",
        )

    @patch("boto3.client")
    @patch("boto3.resource")
    async def test_build_with_docker_remote_success(
        self, mock_boto3_resource: mock.MagicMock, mock_boto3_client: mock.MagicMock
    ):
        # Setup mock for AWS boto3 client
        mock_codebuild = mock.MagicMock()
        mock_codebuild.start_build.return_value = {
            "build": {"id": "test-build-id-remote"}
        }
        mock_codebuild.batch_get_builds.return_value = {
            "builds": [{"buildStatus": "SUCCEEDED"}]
        }
        mock_s3 = mock.MagicMock()
        mock_bucket = mock.MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        mock_boto3_client.return_value = mock_codebuild
        mock_boto3_resource.return_value = mock_s3

        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        result = await builder.build_with_docker_remote(
            "Dockerfile", "test-docker-codebuild-project-name"
        )

        # Validation
        expected_image_name = f"{self.ecr_repository}:{self.launchflow_deployment_id}"
        self.assertEqual(expected_image_name, result)

        mock_boto3_client.assert_any_call(
            "codebuild", region_name=self.aws_environment_config.region
        )

        mock_codebuild.start_build.assert_called_once_with(
            projectName="test-docker-codebuild-project-name",
            sourceTypeOverride="S3",
            sourceLocationOverride="mock_bucket/builds/mock_project/mock_environment/services/mock_service/",
            environmentVariablesOverride=[
                {
                    "name": "IMAGE_TAG",
                    "value": "mock_deployment_id",
                    "type": "PLAINTEXT",
                },
                {"name": "BUILD_TYPE", "value": "docker", "type": "PLAINTEXT"},
                {"name": "BUILD_MODE", "value": "build", "type": "PLAINTEXT"},
                {"name": "DOCKERFILE_PATH", "value": "Dockerfile"},
            ],
        )
        mock_bucket.upload_fileobj.assert_called_once()

    @patch("boto3.client")
    @patch("boto3.resource")
    async def test_build_with_docker_remote_failure(
        self, mock_boto3_resource: mock.MagicMock, mock_boto3_client: mock.MagicMock
    ):
        # Setup mock for AWS boto3 client
        mock_codebuild = mock.MagicMock()
        mock_codebuild.start_build.return_value = {
            "build": {"id": "test-build-id-remote-failure"}
        }
        mock_codebuild.batch_get_builds.return_value = {
            "builds": [{"buildStatus": "FAILED"}]
        }
        mock_s3 = mock.MagicMock()
        mock_bucket = mock.MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        mock_boto3_client.return_value = mock_codebuild
        mock_boto3_resource.return_value = mock_s3

        builder = ECRDockerBuilder(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            build_log_file=self.temp_output_handler,
            ecr_repository=self.ecr_repository,
            launchflow_project_name=self.launchflow_project_name,
            launchflow_environment_name=self.launchflow_environment_name,
            launchflow_service_name=self.launchflow_service_name,
            launchflow_deployment_id=self.launchflow_deployment_id,
            aws_environment_config=self.aws_environment_config,
        )

        with self.assertRaises(ValueError):
            await builder.build_with_docker_remote(
                "Dockerfile", "test-docker-codebuild-project-failure"
            )


if __name__ == "__main__":
    unittest.main()
