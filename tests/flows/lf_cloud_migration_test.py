import datetime
import json
import os
import unittest
from unittest import mock

import pytest
from pytest_httpx import HTTPXMock

import launchflow
from launchflow.backend import LaunchFlowBackend, LocalBackend
from launchflow.flows.lf_cloud_migration import migrate
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.enums import (
    CloudProvider,
    DeploymentProduct,
    DeploymentStatus,
    EnvironmentStatus,
    EnvironmentType,
    ResourceProduct,
    ResourceStatus,
)
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
    ProjectState,
    ResourceState,
    ServiceState,
)


# TODO: add tests for gcs
@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class LFCloudMigrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

        launchflow.lf_config.env.api_key = "key"

        self.backend: LocalBackend = self.launchflow_yaml.backend

        self.now = datetime.datetime(2021, 1, 1, 0, 0, 0, 0)

        self.project = ProjectState(
            name="unittest", created_at=self.now, updated_at=self.now
        )
        self.pm = ProjectManager(project_name="unittest", backend=self.backend)
        await self.pm.save_project_state(self.project)

        self.em = self.pm.create_environment_manager("dev")
        self.environment = EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            status=EnvironmentStatus.READY,
            environment_type=EnvironmentType.DEVELOPMENT,
            gcp_config=GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            aws_config=AWSEnvironmentConfig(
                account_id="test-account",
                region="us-west-2",
                iam_role_arn="test-arn",
                vpc_id="test-vpc",
                artifact_bucket="test-bucket",
            ),
        )
        await self.em.save_environment(self.environment, "lock")

        self.rm = self.em.create_resource_manager("test-storage-bucket")
        self.resource = ResourceState(
            created_at=datetime.datetime(
                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            ),
            updated_at=datetime.datetime(
                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            ),
            name="test-storage-bucket",
            cloud_provider=CloudProvider.GCP,
            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
            gcp_id=None,
            aws_arn=None,
            inputs={"location": "US", "force_destroy": "false"},
            status=ResourceStatus.CREATING,
        )
        await self.rm.save_resource(self.resource, "lock")

        self.sm = self.em.create_service_manager("test-service")
        self.service = ServiceState(
            name="test-service",
            created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            updated_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            cloud_provider=CloudProvider.AWS,
            product=DeploymentProduct.AWS_ECS_FARGATE,
            status=DeploymentStatus.READY,
        )
        await self.sm.save_service(self.service, "lock")

    def setup_base_httpx_mocks(self):
        # Mock the project not existing
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest?account_id=123456789012",
            method="GET",
            status_code=404,
        )
        # Mock the environment not existing
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev?account_id=123456789012",
            method="GET",
            status_code=404,
        )
        # Mock the environment being locked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/lock?account_id=123456789012",
            method="POST",
            json={
                "lock_id": "lock",
                "lock_operation": {
                    "operation_type": "migrate_environment",
                    "metadata": {},
                },
            },
        )
        # Mock the environment being created
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev?lock_id=lock&account_id=123456789012",
            method="POST",
            json=self.environment.to_dict(),
        )
        # Mock the environment being unlocked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/unlock?lock_id=lock&account_id=123456789012",
            method="POST",
        )
        # Mock the resource not existing
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/resources/test-storage-bucket?account_id=123456789012",
            method="GET",
            status_code=404,
        )
        # Mock the resource being locked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/resources/test-storage-bucket/lock?account_id=123456789012",
            method="POST",
            json={
                "lock_id": "lock",
                "lock_operation": {
                    "operation_type": "migrate_resource",
                    "metadata": {},
                },
            },
        )
        # Mock the resource being created
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/resources/test-storage-bucket?lock_id=lock&account_id=123456789012",
            method="POST",
            json=self.resource.to_dict(),
        )
        # Mock the resource being unlocked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/resources/test-storage-bucket/unlock?lock_id=lock&account_id=123456789012",
            method="POST",
        )
        # Mock the service not existing
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/services/test-service?account_id=123456789012",
            method="GET",
            status_code=404,
        )
        # Mock the service being locked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/services/test-service/lock?account_id=123456789012",
            method="POST",
            json={
                "lock_id": "lock",
                "lock_operation": {
                    "operation_type": "migrate_service",
                    "metadata": {},
                },
            },
        )
        # Mock the service being created
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/services/test-service?lock_id=lock&account_id=123456789012",
            method="POST",
            json=self.service.to_dict(),
        )
        # Mock the service being unlocked
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/services/test-service/unlock?lock_id=lock&account_id=123456789012",
            method="POST",
        )

    @pytest.fixture(autouse=True)
    def httpx_pytest_fixture(self, httpx_mock: HTTPXMock):
        self.httpx_mock = httpx_mock

    @mock.patch(
        "launchflow.flows.lf_cloud_migration.config.get_account_id",
        return_value="123456789012",
    )
    @mock.patch("launchflow.flows.lf_cloud_migration.create_project")
    async def test_migrate_all_success_no_tofu(
        self, create_project_mock: mock.AsyncMock, account_mock
    ):
        self.setup_base_httpx_mocks()
        lf_backend = LaunchFlowBackend()
        await migrate(source=self.backend, target=lf_backend)

        create_project_mock.assert_called_once_with(
            client=mock.ANY,
            account_id="123456789012",
            project_name="unittest",
            prompt=True,
        )

    @mock.patch(
        "launchflow.flows.lf_cloud_migration.config.get_account_id",
        return_value="123456789012",
    )
    @mock.patch("launchflow.flows.lf_cloud_migration.create_project")
    async def test_migrate_all_success_with_tofu(
        self, create_project_mock: mock.AsyncMock, account_mock
    ):
        self.setup_base_httpx_mocks()

        # Write environment tofu state
        env_tofu_path = os.path.join(
            self.backend.path, "unittest", "dev", "default.tfstate"
        )
        with open(env_tofu_path, "w") as f:
            json.dump({"env": "dev"}, f)
        # Write resource tofu state
        resource_tofu_path = os.path.join(
            self.backend.path,
            "unittest",
            "dev",
            "resources",
            "test-storage-bucket",
            "module",
            "default.tfstate",
        )
        os.mkdir(os.path.dirname(resource_tofu_path))
        with open(resource_tofu_path, "w") as f:
            json.dump({"resource": "dev"}, f)

        # Write service tofu state
        service_tofu_path = os.path.join(
            self.backend.path,
            "unittest",
            "dev",
            "services",
            "test-service",
            "module",
            "default.tfstate",
        )
        os.mkdir(os.path.dirname(service_tofu_path))
        with open(service_tofu_path, "w") as f:
            json.dump({"service": "dev"}, f)

        # Mock environment write tofu state
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/tofu-state?lock_id=lock&account_id=123456789012",
            method="POST",
            match_json={"env": "dev"},
        )
        lf_backend = LaunchFlowBackend()

        # Mock resource write tofu state
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/resources/test-storage-bucket/tofu-state/module?lock_id=lock&account_id=123456789012",
            method="POST",
            match_json={"resource": "dev"},
        )

        # Mock service write tofu state
        self.httpx_mock.add_response(
            url="https://cloud.launchflow.com/v1/projects/unittest/environments/dev/services/test-service/tofu-state/module?lock_id=lock&account_id=123456789012",
            method="POST",
            match_json={"service": "dev"},
        )

        await migrate(source=self.backend, target=lf_backend)


if __name__ == "__main__":
    unittest.main()
