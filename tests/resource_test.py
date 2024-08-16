import datetime
import os
import tempfile
import unittest
import uuid
from dataclasses import dataclass
from unittest import mock

import pytest
import yaml

from launchflow.cache import cache
from launchflow.config import config
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models.enums import EnvironmentStatus, EnvironmentType, ResourceProduct
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
)
from launchflow.node import Outputs
from launchflow.resource import Resource


@dataclass
class FakeResourceOutputs(Outputs):
    field: str


class FakeResource(Resource[FakeResourceOutputs]):
    product = ResourceProduct.GCP_STORAGE_BUCKET

    def __init__(self, name: str):
        super().__init__(name)


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class ResourceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = self.launchflow_yaml.backend
        self.environment_manager = EnvironmentManager(
            backend=self.backend,
            project_name=self.launchflow_yaml.project,
            environment_name=self.launchflow_yaml.default_environment,
        )
        self.resource = FakeResource(name="test-resource")

    async def asyncTearDown(self):
        cache.delete_resource_outputs(
            self.environment_manager.project_name,
            self.environment_manager.environment_name,
            self.resource.product.value,
            self.resource.name,
        )

    async def test_connect_sync_mounted_volume(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config.env.outputs_path = tempdir

            want = FakeResourceOutputs(field="test-volume")
            os.makedirs(os.path.join(tempdir, "test-resource"), exist_ok=True)
            with open(os.path.join(tempdir, "test-resource", "latest"), "w") as f:
                yaml.safe_dump(want.to_dict(), f)

            got = self.resource.outputs()

            self.assertEqual(got, want)

    async def test_connect_async_mounted_volume(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config.env.outputs_path = tempdir

            want = FakeResourceOutputs(field="test-volume")
            os.makedirs(os.path.join(tempdir, "test-resource"), exist_ok=True)
            with open(os.path.join(tempdir, "test-resource", "latest"), "w") as f:
                yaml.safe_dump(want.to_dict(), f)

            got = await self.resource.outputs_async()

            self.assertEqual(got, want)

    @pytest.mark.skip("Not implemented")
    async def test_connect_sync_cache(self):
        want = FakeResourceOutputs(field=f"test-{str(uuid.uuid4())}")

        cache.set_resource_outputs(
            self.environment_manager.project_name,
            self.environment_manager.environment_name,
            self.resource.product.value,
            self.resource.name,
            want.to_dict(),
        )

        got = self.resource.outputs()

        self.assertEqual(got, want)

    @pytest.mark.skip("Not implemented")
    async def test_connect_async_cache(self):
        want = FakeResourceOutputs(field=f"test-{str(uuid.uuid4())}")

        cache.set_resource_outputs(
            self.environment_manager.project_name,
            self.environment_manager.environment_name,
            self.resource.product.value,
            self.resource.name,
            want.to_dict(),
        )

        got = await self.resource.outputs_async()

        self.assertEqual(got, want)

    @mock.patch("launchflow.resource.read_file")
    async def test_connect_sync_remote_bucket_aws(self, read_file_mock: mock.MagicMock):
        self.resource.product = ResourceProduct.AWS_S3_BUCKET
        want = FakeResourceOutputs(field=f"test-{str(uuid.uuid4())}")
        yaml_str = yaml.safe_dump(want.to_dict())
        with mock.patch(
            "launchflow.resource.read_file",
            new_callable=mock.mock_open,
            read_data=yaml_str,
        ) as read_file_mock:
            self.environment = EnvironmentState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                status=EnvironmentStatus.READY,
                environment_type=EnvironmentType.DEVELOPMENT,
                gcp_config=None,
                aws_config=AWSEnvironmentConfig(
                    account_id="test-account",
                    region="us-west-2",
                    iam_role_arn="test-arn",
                    vpc_id="test-vpc",
                    artifact_bucket="test-bucket",
                ),
            )
            await self.environment_manager.save_environment(
                environment_state=self.environment, lock_id="lock"
            )

            got = self.resource.outputs()

            self.assertEqual(got, want)

            read_file_mock.assert_called_once_with(
                "s3://test-bucket/resources/test-resource.yaml"
            )

    async def test_connect_sync_remote_bucket_gcp(self):
        want = FakeResourceOutputs(field=f"test-{str(uuid.uuid4())}")
        yaml_str = yaml.safe_dump(want.to_dict())
        with mock.patch(
            "launchflow.resource.read_file",
            new_callable=mock.mock_open,
            read_data=yaml_str,
        ) as read_file_mock:
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
                aws_config=None,
            )
            await self.environment_manager.save_environment(
                environment_state=self.environment, lock_id="lock"
            )

            got = self.resource.outputs()

            self.assertEqual(got, want)

            read_file_mock.assert_called_once_with(
                "gs://test-bucket/resources/test-resource.yaml"
            )

    async def test_connect_async_remote_bucket(self):
        want = FakeResourceOutputs(field=f"test-{str(uuid.uuid4())}")
        yaml_str = yaml.safe_dump(want.to_dict())
        with mock.patch(
            "launchflow.resource.read_file",
            new_callable=mock.mock_open,
            read_data=yaml_str,
        ) as read_file_mock:
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
                aws_config=None,
            )
            await self.environment_manager.save_environment(
                environment_state=self.environment, lock_id="lock"
            )

            got = await self.resource.outputs_async()

            self.assertEqual(got, want)

            read_file_mock.assert_called_once_with(
                "gs://test-bucket/resources/test-resource.yaml"
            )


if __name__ == "__main__":
    unittest.main()
