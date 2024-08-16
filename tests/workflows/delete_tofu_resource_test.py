import datetime
import unittest
from unittest import mock

import boto3
import pytest
from google.api_core.exceptions import NotFound
from moto.core.decorator import mock_aws

from launchflow.backend import LocalBackend
from launchflow.models.enums import CloudProvider, ResourceProduct, ResourceStatus
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    GCPEnvironmentConfig,
    ResourceState,
)
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.workflows.commands.tf_commands import TFDestroyCommand
from launchflow.workflows.destroy_resource_tofu.delete_tofu_resource import (
    delete_tofu_resource,
)
from launchflow.workflows.destroy_resource_tofu.schemas import DestroyResourceTofuInputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class TestDeleteTofuResource(unittest.IsolatedAsyncioTestCase):
    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.run_tofu"
    )
    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.get_storage_client"
    )
    async def test_delete_tofu_gcp_resource_sucess(
        self, storage_mock: mock.MagicMock, run_tofu_mock: mock.MagicMock
    ):
        inputs = DestroyResourceTofuInputs(
            launchflow_uri=LaunchFlowURI(
                project_name="project_name",
                environment_name="environment_name",
                resource_name="resource_name",
            ),
            backend=LocalBackend(path="."),
            logs_file="logs_file",
            gcp_env_config=GCPEnvironmentConfig(
                project_id="project_id",
                artifact_bucket="artifact_bucket",
                default_zone="default_zone",
                default_region="default_region",
                service_account_email="service_account_email",
            ),
            aws_env_config=None,
            resource=ResourceState(
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                name="bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_SQL_USER,
                status=ResourceStatus.READY,
            ),
            lock_id="lock_id",
        )

        await delete_tofu_resource(inputs)

        run_tofu_mock.assert_called_once_with(
            TFDestroyCommand(
                tf_module_dir="empty/gcp_empty",
                backend=LocalBackend(path="."),
                tf_state_prefix=mock.ANY,
                logs_file="logs_file",
                launchflow_state_url=None,
                tf_vars={"gcp_project_id": "project_id"},
            )
        )
        storage_mock().bucket.assert_called_once_with("artifact_bucket")
        storage_mock().bucket().blob.assert_called_once_with(
            "resources/resource_name.yaml"
        )
        storage_mock().bucket().blob().delete.assert_called_once_with()

    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.run_tofu"
    )
    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.get_storage_client"
    )
    async def test_delete_tofu_gcp_resource_not_found(
        self, storage_mock: mock.MagicMock, run_tofu_mock: mock.MagicMock
    ):
        inputs = DestroyResourceTofuInputs(
            launchflow_uri=LaunchFlowURI(
                project_name="project_name",
                environment_name="environment_name",
                resource_name="resource_name",
            ),
            backend=LocalBackend(path="."),
            logs_file="logs_file",
            gcp_env_config=GCPEnvironmentConfig(
                project_id="project_id",
                artifact_bucket="artifact_bucket",
                default_zone="default_zone",
                default_region="default_region",
                service_account_email="service_account_email",
            ),
            aws_env_config=None,
            resource=ResourceState(
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                name="bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_SQL_USER,
                status=ResourceStatus.READY,
            ),
            lock_id="lock_id",
        )

        storage_mock().bucket().blob().delete.side_effect = NotFound("not found")

        # Verify that this does not raise errors
        await delete_tofu_resource(inputs)

    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.run_tofu"
    )
    async def test_delete_tofu_aws_resource_sucess(self, run_tofu_mock: mock.MagicMock):
        with mock_aws():
            s3_client = boto3.client("s3")
            s3_client.create_bucket(
                Bucket="artifact_bucket",
                CreateBucketConfiguration={"LocationConstraint": "region"},
            )
            s3_client.put_object(
                Bucket="artifact_bucket",
                Key="resources/resource_name.yaml",
                Body="my-data",
            )

            inputs = DestroyResourceTofuInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="project_name",
                    environment_name="environment_name",
                    resource_name="resource_name",
                ),
                backend=LocalBackend(path="."),
                logs_file="logs_file",
                gcp_env_config=None,
                aws_env_config=AWSEnvironmentConfig(
                    account_id="account_id",
                    region="region",
                    artifact_bucket="artifact_bucket",
                    iam_role_arn="iam_role_arn",
                    vpc_id="vpc_id",
                ),
                resource=ResourceState(
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    name="bucket",
                    cloud_provider=CloudProvider.AWS,
                    product=ResourceProduct.AWS_EC2,
                    status=ResourceStatus.READY,
                ),
                lock_id="lock_id",
            )

            await delete_tofu_resource(inputs)

            run_tofu_mock.assert_called_once_with(
                TFDestroyCommand(
                    tf_module_dir="empty/aws_empty",
                    backend=LocalBackend(path="."),
                    tf_state_prefix=mock.ANY,
                    logs_file="logs_file",
                    launchflow_state_url=None,
                    tf_vars={"aws_region": "region"},
                )
            )

            with self.assertRaises(s3_client.exceptions.NoSuchKey):
                s3_client.get_object(
                    Bucket="artifact_bucket",
                    Key="resources/resource_name.yaml",
                )

    @mock.patch(
        "launchflow.workflows.destroy_resource_tofu.delete_tofu_resource.run_tofu"
    )
    async def test_delete_tofu_aws_no_s3_file(self, run_tofu_mock: mock.MagicMock):
        with mock_aws():
            s3_client = boto3.client("s3")
            s3_client.create_bucket(
                Bucket="artifact_bucket",
                CreateBucketConfiguration={"LocationConstraint": "region"},
            )

            inputs = DestroyResourceTofuInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="project_name",
                    environment_name="environment_name",
                    resource_name="resource_name",
                ),
                backend=LocalBackend(path="."),
                logs_file="logs_file",
                gcp_env_config=None,
                aws_env_config=AWSEnvironmentConfig(
                    account_id="account_id",
                    region="region",
                    artifact_bucket="artifact_bucket",
                    iam_role_arn="iam_role_arn",
                    vpc_id="vpc_id",
                ),
                resource=ResourceState(
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    name="bucket",
                    cloud_provider=CloudProvider.AWS,
                    product=ResourceProduct.AWS_EC2,
                    status=ResourceStatus.READY,
                ),
                lock_id="lock_id",
            )

            # Verify that this does not raise errors
            await delete_tofu_resource(inputs)


if __name__ == "__main__":
    unittest.main()
