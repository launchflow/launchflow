import asyncio
import datetime
import json
import tempfile
import unittest
from unittest import mock

import pytest
import yaml
from google.api_core.exceptions import NotFound, PreconditionFailed
from google.cloud import storage
from pytest_httpx import HTTPXMock

from launchflow import exceptions
from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.clients.response_schemas import EnvironmentType
from launchflow.locks import (
    GCSLock,
    LaunchFlowLock,
    LocalLock,
    LockInfo,
    LockOperation,
    OperationType,
)
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.models.enums import CloudProvider, ResourceProduct, ResourceStatus
from launchflow.models.flow_state import EnvironmentState, ResourceState


@pytest.mark.usefixtures("launchflow_yaml_remote_backend_fixture")
class EnvironmentManagerTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_httpx_mock(self, httpx_mock: HTTPXMock):
        self.httpx_mock = httpx_mock

    async def test_local_environment_success(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            env = EnvironmentState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="project",
                environment_type=EnvironmentType.DEVELOPMENT,
            )
            await manager.save_environment(env, "lock_id")

            loaded_env = await manager.load_environment()
            self.assertEqual(loaded_env, env)

    async def test_local_environment_not_found(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            with pytest.raises(exceptions.EnvironmentNotFound):
                await manager.load_environment()

    async def test_local_environment_delete(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            env = EnvironmentState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="project",
                environment_type=EnvironmentType.DEVELOPMENT,
            )
            # Save environment
            await manager.save_environment(env, "lock_id")
            # Load environment to ensure it exists
            await manager.load_environment()
            # Delete environment
            await manager.delete_environment("lock_id")
            # Reload the environment to ensure it was deleted
            with pytest.raises(exceptions.EnvironmentNotFound):
                await manager.load_environment()

    async def test_local_environment_delete_cascades(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            env = EnvironmentState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="project",
                environment_type=EnvironmentType.DEVELOPMENT,
            )
            # Save environment
            await manager.save_environment(env, "lock_id")

            # Create a resource in the environment and save it
            resource = ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="resource",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET,
                status=ResourceStatus.READY,
            )
            resource_manager = manager.create_resource_manager("resource")
            await resource_manager.save_resource(resource, "lock_id")

            # Load environment to ensure it exists
            await manager.load_environment()
            # Delete environment
            await manager.delete_environment("lock_id")
            # Reload the environment to ensure it was deleted
            with pytest.raises(exceptions.EnvironmentNotFound):
                await manager.load_environment()
            with pytest.raises(exceptions.ResourceNotFound):
                await resource_manager.load_resource()

    async def test_local_environment_lock_failed(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            lock = await manager.lock_environment(
                operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE)
            )

            self.assertIsInstance(lock, LocalLock)

            with pytest.raises(exceptions.EntityLocked):
                await lock.acquire()

    async def test_local_environment_lock_wait_for_success(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            # get an initial lock
            lock1 = await manager.lock_environment(
                operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE)
            )

            self.assertIsInstance(lock1, LocalLock)

            lock2 = manager.lock_environment(
                operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE),
                wait_for_seconds=3,
            )
            lock_task = asyncio.create_task(lock2)

            await asyncio.sleep(1)
            await lock1.release()
            second_lock = await lock_task
            assert second_lock._lock_info is not None
            # Second lock should result in an already locked exception
            with pytest.raises(exceptions.EntityLocked):
                await second_lock.acquire()

    async def test_local_environment_lock_wait_for_failed(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = EnvironmentManager("project", "dev", backend)
            # get an initial lock
            lock1 = await manager.lock_environment(
                operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE)
            )

            self.assertIsInstance(lock1, LocalLock)

            lock2 = manager.lock_environment(
                operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE),
                wait_for_seconds=3,
            )
            lock_task = asyncio.create_task(lock2)

            await asyncio.sleep(1)
            with pytest.raises(exceptions.EntityLocked):
                await lock_task

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_environment_save_success(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)
        env = EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=EnvironmentType.DEVELOPMENT,
        )
        await manager.save_environment(env, "lock_id")

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with("prefix/project/dev/flow.state")
        blob_mock.upload_from_string.assert_called_with(
            yaml.dump(env.to_dict(), sort_keys=False)
        )

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_environment_load_success(self, mock_storage_client):
        env = EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=EnvironmentType.DEVELOPMENT,
        )
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        def download_as_bytes():
            return yaml.dump(env.to_dict()).encode("utf-8")

        blob_mock.download_as_bytes = download_as_bytes

        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)
        got = await manager.load_environment()

        assert got == env

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_environment_load_not_found(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        def download_as_bytes():
            raise NotFound("not found")

        blob_mock.download_as_bytes = download_as_bytes
        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)
        with pytest.raises(exceptions.EnvironmentNotFound):
            await manager.load_environment()

    @mock.patch("launchflow.managers.environment_manager.get_storage_client")
    async def test_gcs_environment_delete(self, mock_storage_client):
        client_mock = mock.MagicMock()
        blob_mock1 = mock.MagicMock(spec=storage.Blob)
        blob_mock2 = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.list_blobs.return_value = [blob_mock1, blob_mock2]

        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)

        await manager.delete_environment("lock_id")

        blob_mock1.delete.assert_called()
        blob_mock2.delete.assert_called()

    @mock.patch("launchflow.managers.resource_manager.write_to_gcs")
    @mock.patch("launchflow.managers.environment_manager.get_storage_client")
    async def test_gcs_environment_delete_cascades(
        self, mock_storage_client, mock_write_to_gcs
    ):
        client_mock = mock.MagicMock()
        blob_mock1 = mock.MagicMock(spec=storage.Blob)
        blob_mock2 = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.list_blobs.return_value = [blob_mock1, blob_mock2]

        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)
        resource_manager = ResourceManager("project", "dev", "resource", backend)
        await resource_manager.save_resource(
            ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="resource",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET,
                status=ResourceStatus.READY,
            ),
            "lock_id",
        )

        await manager.delete_environment("lock_id")

        client_mock.list_blobs.assert_called()
        blob_mock1.delete.assert_called()
        blob_mock2.delete.assert_called()

        # Deleting the environment state should also delete the resource state, so the resource
        # should have been stored to a path containing the environment prefix
        environment_delete_prefix = client_mock.list_blobs.call_args.kwargs["prefix"]
        resource_write_prefix = mock_write_to_gcs.call_args.args[1]
        self.assertIn(environment_delete_prefix, resource_write_prefix)

    @mock.patch("launchflow.locks.get_storage_client")
    async def test_gcs_environment_lock(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = EnvironmentManager("project", "dev", backend)

        lock = await manager.lock_environment(
            operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE)
        )

        self.assertIsInstance(lock, GCSLock)

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with("prefix/project/dev/flow.lock")
        blob_mock.upload_from_string.assert_called_once_with(
            mock.ANY, if_generation_match=0
        )

        blob_mock.upload_from_string.side_effect = PreconditionFailed("failed")

        with pytest.raises(exceptions.EntityLocked):
            await lock.acquire()

        blob_mock.reset_mock()
        lock_info = LockInfo(
            lock_id="lock_id",
            lock_operation=LockOperation(
                operation_type=OperationType.CREATE_ENVIRONMENT
            ),
        )
        blob_mock.download_as_bytes.return_value = json.dumps(
            lock_info.to_dict(),
        ).encode("utf-8")

        lock._lock_info = lock_info
        await lock.release("lock_id")
        blob_mock.delete.assert_called_once()

    async def test_launchflow_environment_load_success(self):
        env = EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=EnvironmentType.DEVELOPMENT,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = EnvironmentManager("project", "dev", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev?account_id=account_id",
            method="GET",
            json=env.to_dict(),
            match_headers={"Authorization": "Bearer key"},
        )
        got = await manager.load_environment()

        self.assertEqual(got, env)

    async def test_launchflow_environment_save_success(self):
        env = EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
            environment_type=EnvironmentType.DEVELOPMENT,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = EnvironmentManager("project", "dev", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_json=env.to_dict(),
            match_headers={"Authorization": "Bearer key"},
            json=env.to_dict(),
        )
        # This just validates that the request is made correctly
        await manager.save_environment(env, "lock_id")

    async def test_launchflow_environment_load_not_found(self):
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = EnvironmentManager("project", "dev", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev?account_id=account_id",
            method="GET",
            status_code=404,
            match_headers={"Authorization": "Bearer key"},
        )

        with pytest.raises(exceptions.EnvironmentNotFound):
            await manager.load_environment()

    async def test_launchflow_environment_delete(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev?lock_id=lock_id&account_id=account_id",
            method="DELETE",
            match_headers={"Authorization": "Bearer key"},
            json={},
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = EnvironmentManager("project", "dev", backend)

        await manager.delete_environment("lock_id")

    async def test_launchflow_environment_lock(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/lock?account_id=account_id",
            method="POST",
            match_headers={"Authorization": "Bearer key"},
            json=LockInfo(
                lock_id="lock_id",
                lock_operation=LockOperation(
                    operation_type=OperationType.CREATE_ENVIRONMENT
                ),
            ).to_dict(),
        )
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/unlock?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_headers={"Authorization": "Bearer key"},
        )

        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = EnvironmentManager("project", "dev", backend)

        lock = await manager.lock_environment(
            operation=LockOperation(operation_type=OperationType.PROMOTE_SERVICE)
        )

        self.assertIsInstance(lock, LaunchFlowLock)

        await lock.acquire()
        await lock.release()


if __name__ == "__main__":
    unittest.main()
