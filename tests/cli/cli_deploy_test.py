import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from launchflow.cli.main import app
from launchflow.clients.response_schemas import EnvironmentResponse, EnvironmentType
from launchflow.gcp.cloud_run import CloudRunService
from launchflow.gcp.gcs import GCSBucket


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class CLIDeployTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.runner = CliRunner()

    @patch("launchflow.clients.LaunchFlowAsyncClient")
    @patch("launchflow.cli.main.get_environment")
    @patch("launchflow.cli.main.import_services")
    @patch("launchflow.cli.main.deploy_services")
    @patch("launchflow.cli.main.import_resources")
    def test_deploy_with_create(
        self,
        import_resources_mock: MagicMock,
        deploy_services: AsyncMock,
        import_services_mock: MagicMock,
        get_environment_mock: AsyncMock,
        client_mock: AsyncMock,
    ):
        client_mock.return_value.close = AsyncMock()
        get_environment_mock.return_value = (
            "dev",
            EnvironmentResponse(
                name="dev",
                environment_type=EnvironmentType.DEVELOPMENT,
                status="ready",
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                status_message="",
            ),
        )
        import_services_mock.return_value = [
            CloudRunService(name="cloud_run_a"),
            CloudRunService(name="cloud_run_b", cpu=2, memory="2G", region="us-central1"),
        ]

        import_resources_mock.return_value = [GCSBucket(name="bucket")]

        results = self.runner.invoke(app, ["--disable-usage-statistics", "deploy"])

        if results.exception:
            raise results.exception
        self.assertEqual(results.exit_code, 0, results.stdout)

        deploy_services.assert_called_once_with(
            GCSBucket(name="bucket"),
            CloudRunService(name="cloud_run_a"),
            CloudRunService(
                name="cloud_run_b",
                region="us-central1",
                cpu=2,
                memory="2G",
            ),
            environment="dev",
            prompt=True,
            verbose=False,
            build_local=False,
            skip_create=False,
            check_dockerfiles=False,
            skip_build=False,
        )

    @patch("launchflow.clients.LaunchFlowAsyncClient")
    @patch("launchflow.cli.main.get_environment")
    @patch("launchflow.cli.main.find_launchflow_services")
    @patch("launchflow.cli.main.import_services")
    @patch("launchflow.cli.main.deploy_services")
    @patch("launchflow.cli.main.find_launchflow_resources")
    def test_deploy_with_service_ref(
        self,
        find_launchflow_resources_mock: MagicMock,
        deploy_services: AsyncMock,
        import_services_mock: MagicMock,
        find_launchflow_services_mock: MagicMock,
        get_environment_mock: AsyncMock,
        client_mock: AsyncMock,
    ):
        find_launchflow_resources_mock.return_value = []
        client_mock.return_value.close = AsyncMock()
        get_environment_mock.return_value = (
            "dev",
            EnvironmentResponse(
                name="dev",
                environment_type=EnvironmentType.DEVELOPMENT,
                status="ready",
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                status_message="",
            ),
        )
        import_services_mock.return_value = [
            CloudRunService(name="cloud_run_a"),
        ]

        results = self.runner.invoke(
            app,
            [
                "--disable-usage-statistics",
                "deploy",
                "--service=cloud_run_a",
                "--skip-create",
            ],
        )

        self.assertEqual(results.exit_code, 0, results.stdout)

        find_launchflow_services_mock.assert_called_once()

        deploy_services.assert_called_once_with(
            CloudRunService(name="cloud_run_a"),
            environment="dev",
            prompt=True,
            verbose=False,
            build_local=False,
            skip_create=True,
            check_dockerfiles=False,
            skip_build=False,
        )

    @patch("launchflow.clients.LaunchFlowAsyncClient")
    @patch("launchflow.cli.main.get_environment")
    @patch("launchflow.cli.main.import_services")
    @patch("launchflow.cli.main.deploy_services")
    def test_deploy_filter_no_match(
        self,
        deploy_services: AsyncMock,
        import_services_mock: MagicMock,
        get_environment_mock: AsyncMock,
        client_mock: AsyncMock,
    ):
        client_mock.return_value.close = AsyncMock()
        get_environment_mock.return_value = (
            "dev",
            EnvironmentResponse(
                name="dev",
                environment_type=EnvironmentType.DEVELOPMENT,
                status="ready",
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                status_message="",
            ),
        )
        import_services_mock.return_value = []

        results = self.runner.invoke(
            app,
            ["--disable-usage-statistics", "deploy", "--service=bad", "--skip-create"],
        )

        self.assertEqual(results.exit_code, 1, results.stdout)

        deploy_services.assert_not_called()


if __name__ == "__main__":
    unittest.main()
