import asyncio
import datetime
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

import pytest
from freezegun import freeze_time
from moto import mock_aws

from launchflow import exceptions
from launchflow.config.launchflow_yaml import LocalBackend
from launchflow.flows import environments_flows
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.models import enums, flow_state
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.workflows.aws_env_creation.schemas import (
    AWSEnvironmentCreationInputs,
    AWSEnvironmentCreationOutputs,
)
from launchflow.workflows.aws_env_deletion.schemas import AWSEnvironmentDeletionInputs
from launchflow.workflows.gcp_env_creation.schemas import (
    GCPEnvironmentCreationInputs,
    GCPEnvironmentCreationOutputs,
)
from launchflow.workflows.gcp_env_deletion.schemas import GCPEnvironmentDeletionInputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class EnvironmentFlowTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_capsys(self, capsys):
        self.capsys = capsys

    async def asyncSetUp(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
        tempdir = tempfile.mkdtemp()
        self.backend = LocalBackend(path=tempdir)

    async def asyncTearDown(self):
        os.environ.pop("AWS_DEFAULT_REGION")
        shutil.rmtree(self.backend.path)

    async def test_create_environment_existing_environment_type_mismatch(self):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        with pytest.raises(exceptions.ExistingEnvironmentDifferentEnvironmentType):
            await environments_flows.create_environment(
                enums.EnvironmentType.PRODUCTION, cloud_provider=None, manager=manager
            )

    async def test_create_environment_existing_gcp_environment_type_mismatch(self):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="",
                artifact_bucket="test-bucket",
            ),
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        with pytest.raises(exceptions.ExistingEnvironmentDifferentCloudProvider):
            await environments_flows.create_environment(
                enums.EnvironmentType.DEVELOPMENT,
                cloud_provider=enums.CloudProvider.AWS,
                manager=manager,
            )

    async def test_create_environment_existing_aws_environment_type_mismatch(self):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            aws_config=flow_state.AWSEnvironmentConfig(
                artifact_bucket="test-bucket",
                account_id="123456789012",
                iam_role_arn="test-role-arn",
                region="us-east-1",
                vpc_id="test-vpc-id",
            ),
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        with pytest.raises(exceptions.ExistingEnvironmentDifferentCloudProvider):
            await environments_flows.create_environment(
                enums.EnvironmentType.DEVELOPMENT,
                cloud_provider=enums.CloudProvider.GCP,
                manager=manager,
            )

    @freeze_time("2022-01-01")
    @mock.patch("launchflow.flows.environments_flows.create_gcp_environment")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_environment_new_gcp_success(
        self, uuid_mock, mock_create_gcp_environment: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        mock_create_gcp_environment.return_value = GCPEnvironmentCreationOutputs(
            artifact_bucket="test-bucket",
            vpc_connection_managed=True,
            environment_service_account_email="test-email",
            gcp_project_id="test-project",
            success=True,
        )
        await environments_flows.create_environment(
            enums.EnvironmentType.DEVELOPMENT,
            enums.CloudProvider.GCP,
            manager=manager,
            gcp_organization_name="org",
        )
        mock_create_gcp_environment.assert_called_once_with(
            inputs=GCPEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                lock_id="lock",
                gcp_project_id=None,
                environment_service_account_email=None,
                artifact_bucket=None,
                org_name="org",
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            ),
            prompt=True,
        )

        got_env = await manager.load_environment()
        want_env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
        )
        self.assertEqual(got_env, want_env)

        captured = self.capsys.readouterr()
        assert "Environment created successfully!\n" in captured.out

    @freeze_time(datetime.datetime(2022, 1, 1))
    @mock.patch("launchflow.flows.environments_flows.create_gcp_environment")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_gcp_environment_existing_success(
        self, uuid_mock, mock_create_gcp_environment: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        existing_env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="sa@sa.com",
                artifact_bucket="test-bucket",
                vpc_connection_managed=True,
            ),
        )
        await manager.save_environment(environment_state=existing_env, lock_id="lock")
        want_env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project2",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
        )
        mock_create_gcp_environment.return_value = GCPEnvironmentCreationOutputs(
            artifact_bucket="test-bucket",
            vpc_connection_managed=True,
            environment_service_account_email="test-email",
            gcp_project_id="test-project2",
            success=True,
        )
        got_env = await environments_flows.create_environment(
            enums.EnvironmentType.DEVELOPMENT, enums.CloudProvider.GCP, manager=manager
        )
        mock_create_gcp_environment.assert_called_once_with(
            inputs=GCPEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                gcp_project_id="test-project",
                environment_service_account_email="sa@sa.com",
                artifact_bucket="test-bucket",
                lock_id="lock",
                vpc_connection_managed=True,
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            ),
            prompt=True,
        )

        got_env = await manager.load_environment()
        self.assertEqual(got_env, want_env)

    @freeze_time(datetime.datetime(2022, 1, 1))
    @mock.patch("launchflow.flows.environments_flows.create_gcp_environment")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_gcp_environment_new_failed(
        self, uuid_mock, mock_create_gcp_environment: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        mock_create_gcp_environment.return_value = GCPEnvironmentCreationOutputs(
            artifact_bucket=None,
            vpc_connection_managed=True,
            environment_service_account_email=None,
            gcp_project_id="project",
            success=False,
        )
        got_env = await environments_flows.create_environment(
            enums.EnvironmentType.DEVELOPMENT,
            enums.CloudProvider.GCP,
            manager=manager,
            gcp_organization_name="org",
        )
        mock_create_gcp_environment.assert_called_once_with(
            inputs=GCPEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                gcp_project_id=None,
                environment_service_account_email=None,
                vpc_connection_managed=None,
                artifact_bucket=None,
                lock_id="lock",
                org_name="org",
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            ),
            prompt=True,
        )

        saved_env = await manager.load_environment()
        self.assertEqual(
            saved_env,
            flow_state.EnvironmentState(
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                gcp_config=flow_state.GCPEnvironmentConfig(
                    project_id="project",
                    default_region="us-central1",
                    default_zone="us-central1-a",
                    service_account_email=None,
                    artifact_bucket=None,
                ),
                status=enums.EnvironmentStatus.CREATE_FAILED,
            ),
        )
        assert got_env is None

        captured = self.capsys.readouterr()
        assert "✗ Failed to create environment." in captured.out

    @mock.patch("launchflow.flows.environments_flows.create_gcp_environment")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_gcp_environment_locked(
        self, uuid_mock, mock_create_gcp_environment: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )

        async def sleep(*args, **kwargs):
            await asyncio.sleep(1)

        mock_create_gcp_environment.side_effect = sleep

        task = asyncio.create_task(
            environments_flows.create_environment(
                enums.EnvironmentType.DEVELOPMENT,
                enums.CloudProvider.GCP,
                manager=manager,
                gcp_organization_name="org",
            )
        )

        # Wait for the lock to get held
        await asyncio.sleep(0.2)
        with pytest.raises(exceptions.EntityLocked):
            await environments_flows.create_environment(
                enums.EnvironmentType.DEVELOPMENT,
                enums.CloudProvider.GCP,
                manager=manager,
            )
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_aws_environment_new_success(self, uuid_mock):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        with mock_aws():
            with mock.patch("beaupy.confirm") as input_mock:
                input_mock.return_value = True
                with mock.patch("beaupy.select") as select_mock:
                    # This should point to us-west-2 since it's the default region for the test
                    select_mock.return_value = 0
                    with mock.patch(
                        "launchflow.flows.environments_flows.create_aws_environment"
                    ) as mock_create_aws_environment:
                        mock_create_aws_environment.return_value = (
                            AWSEnvironmentCreationOutputs(
                                artifact_bucket="test-bucket",
                                role_arn="test-role-arn",
                                vpc_id="test-vpc-id",
                                success=True,
                            )
                        )
                        got_env = await environments_flows.create_environment(
                            enums.EnvironmentType.DEVELOPMENT,
                            enums.CloudProvider.AWS,
                            manager=manager,
                        )
        mock_create_aws_environment.assert_called_once_with(
            inputs=AWSEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                aws_account_id="123456789012",
                artifact_bucket=None,
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                region="us-west-2",
                lock_id="lock",
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            )
        )
        want_env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                artifact_bucket="test-bucket",
                account_id="123456789012",
                iam_role_arn="test-role-arn",
                region="us-west-2",
                vpc_id="test-vpc-id",
            ),
        )
        saved_env = await manager.load_environment()
        self.assertEqual(saved_env, want_env)
        self.assertEqual(got_env, want_env)

        captured = self.capsys.readouterr()
        assert "Environment created successfully!\n" in captured.out

    @freeze_time(datetime.datetime(2022, 1, 1))
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_aws_environment_existing_success(self, uuid_mock):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        await manager.save_environment(
            flow_state.EnvironmentState(
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                aws_config=flow_state.AWSEnvironmentConfig(
                    artifact_bucket="test-bucket",
                    account_id="123456789012",
                    iam_role_arn=None,
                    region="us-east-1",
                    vpc_id=None,
                ),
            ),
            "lock",
        )
        with mock_aws():
            with mock.patch(
                "launchflow.flows.environments_flows.create_aws_environment"
            ) as mock_create_aws_environment:
                mock_create_aws_environment.return_value = (
                    AWSEnvironmentCreationOutputs(
                        artifact_bucket="test-bucket",
                        role_arn="test-role-arn",
                        vpc_id="test-vpc-id",
                        success=True,
                    )
                )
                await environments_flows.create_environment(
                    enums.EnvironmentType.DEVELOPMENT,
                    enums.CloudProvider.AWS,
                    manager=manager,
                )
        mock_create_aws_environment.assert_called_once_with(
            inputs=AWSEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                aws_account_id="123456789012",
                artifact_bucket="test-bucket",
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                region="us-east-1",
                lock_id="lock",
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            )
        )

        saved_env = await manager.load_environment()
        self.assertEqual(
            saved_env,
            flow_state.EnvironmentState(
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                aws_config=flow_state.AWSEnvironmentConfig(
                    artifact_bucket="test-bucket",
                    account_id="123456789012",
                    iam_role_arn="test-role-arn",
                    region="us-east-1",
                    vpc_id="test-vpc-id",
                ),
            ),
        )

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_create_aws_environment_new_failed(self, uuid_mock):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        with mock_aws():
            with mock.patch("beaupy.confirm") as input_mock:
                input_mock.return_value = True
                with mock.patch("beaupy.select") as select_mock:
                    # This should point to us-west-2 since it's the default region for the test
                    select_mock.return_value = 0
                    with mock.patch(
                        "launchflow.flows.environments_flows.create_aws_environment"
                    ) as mock_create_aws_environment:
                        mock_create_aws_environment.return_value = (
                            AWSEnvironmentCreationOutputs(
                                artifact_bucket="test-bucket",
                                role_arn=None,
                                vpc_id=None,
                                success=False,
                            )
                        )
                        got_env = await environments_flows.create_environment(
                            enums.EnvironmentType.DEVELOPMENT,
                            enums.CloudProvider.AWS,
                            manager=manager,
                        )
        mock_create_aws_environment.assert_called_once_with(
            inputs=AWSEnvironmentCreationInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                ),
                aws_account_id="123456789012",
                artifact_bucket=None,
                environment_type=enums.EnvironmentType.DEVELOPMENT,
                region="us-west-2",
                lock_id="lock",
                logs_file=f"/tmp/launchflow/create-environment-dev-{int(time.time())}.log",
            )
        )
        want_env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                artifact_bucket="test-bucket",
                account_id="123456789012",
                iam_role_arn=None,
                region="us-west-2",
                vpc_id=None,
            ),
            status=enums.EnvironmentStatus.CREATE_FAILED,
        )
        saved_env = await manager.load_environment()
        self.assertEqual(saved_env, want_env)
        self.assertIsNone(got_env)

        captured = self.capsys.readouterr()
        assert "✗ Failed to create environment." in captured.out

    @mock.patch("beaupy.select")
    async def test_get_environment_existing(self, beaupy_select_mock: mock.MagicMock):
        beaupy_select_mock.return_value = "dev"
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        project_state_manager = ProjectManager(
            project_name="unittest",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        _, got_env = await environments_flows.get_environment(
            project_state_manager=project_state_manager
        )
        self.assertEqual(got_env, env)

    @mock.patch("beaupy.select")
    @mock.patch("launchflow.flows.environments_flows.create_environment")
    @mock.patch("beaupy.prompt")
    async def test_get_environment_no_env_provided_select_non_existing(
        self,
        prompt_mock: str,
        create_env_flow: mock.AsyncMock,
        beaupy_select_mock: mock.MagicMock,
    ):
        beaupy_select_mock.return_value = "[i yellow]Create new environment[/i yellow]"
        prompt_mock.return_value = "dev"
        want_env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
        )
        create_env_flow.return_value = want_env
        project_state_manager = ProjectManager(
            project_name="unittest",
            backend=self.backend,
        )
        _, got_env = await environments_flows.get_environment(
            project_state_manager=project_state_manager
        )
        self.assertEqual(got_env, want_env)
        create_env_flow.assert_called_once()

    async def test_get_environment_env_provided_and_exists(self):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        project_state_manager = ProjectManager(
            project_name="unittest",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        _, got_env = await environments_flows.get_environment(
            project_state_manager=project_state_manager, environment_name="dev"
        )

        self.assertEqual(got_env, env)

    @mock.patch("beaupy.confirm", return_value=True)
    @mock.patch("launchflow.flows.environments_flows.create_environment")
    async def test_get_environment_env_provided_not_exists(
        self, create_env_flow: mock.AsyncMock, confirm_mock: mock.MagicMock
    ):
        project_state_manager = ProjectManager(
            project_name="unittest",
            backend=self.backend,
        )
        want_env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=enums.EnvironmentType.DEVELOPMENT,
        )
        create_env_flow.return_value = want_env
        _, got_env = await environments_flows.get_environment(
            project_state_manager=project_state_manager, environment_name="dev"
        )

        self.assertEqual(got_env, want_env)
        create_env_flow.assert_called_once()

    @freeze_time("2022-01-01")
    @mock.patch("launchflow.flows.environments_flows.delete_gcp_environment")
    async def test_delete_gcp_environment_success(
        self, delete_gcp_env_mock: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")

        await environments_flows.delete_environment(manager, detach=False, prompt=False)

        delete_gcp_env_mock.assert_called_once_with(
            inputs=GCPEnvironmentDeletionInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest", environment_name="dev"
                ),
                environment_state=env,
            )
        )

        with self.assertRaises(exceptions.EnvironmentNotFound):
            await manager.load_environment()

    @freeze_time("2022-01-01")
    @mock.patch("launchflow.flows.environments_flows.delete_gcp_environment")
    async def test_delete_gcp_environment_detach(
        self, delete_gcp_env_mock: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")

        await environments_flows.delete_environment(manager, detach=True, prompt=False)

        delete_gcp_env_mock.assert_not_called()

        with self.assertRaises(exceptions.EnvironmentNotFound):
            await manager.load_environment()

    @freeze_time("2022-01-01")
    @mock.patch("launchflow.flows.environments_flows.delete_gcp_environment")
    async def test_delete_gcp_environment_failed(
        self, delete_gcp_env_mock: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")

        delete_gcp_env_mock.side_effect = ValueError("Failed to delete environment")

        with self.assertRaises(ValueError):
            await environments_flows.delete_environment(
                manager, detach=False, prompt=False
            )

        new_env = await manager.load_environment()
        self.assertEqual(new_env.status, enums.EnvironmentStatus.DELETE_FAILED)

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("launchflow.flows.environments_flows.delete_aws_environment")
    async def test_delete_aws_environment_success(
        self, delete_aws_env_mock: mock.MagicMock, uuid_mock: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="123456789012",
                artifact_bucket="test-bucket",
                iam_role_arn="test-role-arn",
                region="us-east-1",
                vpc_id="test-vpc-id",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")

        await environments_flows.delete_environment(manager, detach=False, prompt=False)

        delete_aws_env_mock.assert_called_once_with(
            inputs=AWSEnvironmentDeletionInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest", environment_name="dev"
                ),
                aws_region="us-east-1",
                artifact_bucket="test-bucket",
                lock_id="lock",
                logs_file=f"/tmp/launchflow/delete-aws-environment-dev-{int(time.time())}.log",
            )
        )

        with self.assertRaises(exceptions.EnvironmentNotFound):
            await manager.load_environment()

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("launchflow.flows.environments_flows.delete_aws_environment")
    async def test_delete_aws_environment_failed(
        self, delete_aws_env_mock: mock.MagicMock, uuid_mock: mock.MagicMock
    ):
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="123456789012",
                artifact_bucket="test-bucket",
                iam_role_arn="test-role-arn",
                region="us-east-1",
                vpc_id="test-vpc-id",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")

        delete_aws_env_mock.side_effect = ValueError("Failed to delete environment")

        with self.assertRaises(ValueError):
            await environments_flows.delete_environment(
                manager, detach=False, prompt=False
            )

        new_env = await manager.load_environment()
        self.assertEqual(new_env.status, enums.EnvironmentStatus.DELETE_FAILED)

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_delete_environment_with_resources(self, uuid_mock: mock.MagicMock):
        env_manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env_with_resources = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="123456789012",
                artifact_bucket="test-bucket",
                iam_role_arn="test-role-arn",
                region="us-east-1",
                vpc_id="test-vpc-id",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await env_manager.save_environment(
            environment_state=env_with_resources, lock_id="lock"
        )
        resource_manager = env_manager.create_resource_manager("test-resource")
        await resource_manager.save_resource(
            flow_state.ResourceState(
                name="test-resource",
                created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ResourceProduct.AWS_S3_BUCKET,
                status=enums.ResourceStatus.READY,
            ),
            lock_id="lock",
        )

        with self.assertRaises(exceptions.EnvironmentNotEmpty):
            await environments_flows.delete_environment(
                env_manager, detach=False, prompt=False
            )

    @freeze_time("2022-01-01")
    @mock.patch("uuid.uuid4", return_value="lock")
    async def test_delete_environment_with_services(self, uuid_mock: mock.MagicMock):
        env_manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )
        env_with_services = flow_state.EnvironmentState(
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="123456789012",
                artifact_bucket="test-bucket",
                iam_role_arn="test-role-arn",
                region="us-east-1",
                vpc_id="test-vpc-id",
            ),
            status=enums.EnvironmentStatus.READY,
        )
        await env_manager.save_environment(
            environment_state=env_with_services, lock_id="lock"
        )
        service_manager = env_manager.create_service_manager("test-service")
        await service_manager.save_service(
            flow_state.ServiceState(
                name="test-service",
                created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.DeploymentProduct.AWS_ECS_FARGATE,
                status=enums.DeploymentStatus.READY,
            ),
            lock_id="lock",
        )

        with self.assertRaises(exceptions.EnvironmentNotEmpty):
            await environments_flows.delete_environment(
                env_manager, detach=False, prompt=False
            )

    async def test_force_unlock_environment_success(self):
        env_manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )

        # Lock the env
        lock = await env_manager.lock_environment(
            LockOperation(operation_type=OperationType.LOCK_ENVIRONMENT)
        )

        # Force unlock the env
        await env_manager.force_unlock_environment()

        # Try to lock the env again to ensure it's unlocked
        lock = await env_manager.lock_environment(
            LockOperation(operation_type=OperationType.LOCK_ENVIRONMENT)
        )
        await lock.release()

    async def test_force_unlock_environment_not_locked(self):
        env_manager = EnvironmentManager(
            project_name="unittest",
            environment_name="dev",
            backend=self.backend,
        )

        with self.assertRaises(exceptions.LockNotFound):
            await env_manager.force_unlock_environment()


if __name__ == "__main__":
    unittest.main()
