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
from launchflow.flows.cloud_provider import CloudProvider
from launchflow.locks import (
    GCSLock,
    LaunchFlowLock,
    LocalLock,
    LockInfo,
    LockOperation,
    OperationType,
)
from launchflow.managers.resource_manager import ResourceManager
from launchflow.models.enums import ResourceProduct, ResourceStatus
from launchflow.models.flow_state import ResourceState


@pytest.mark.usefixtures("launchflow_yaml_remote_backend_fixture")
class ResourceManagerTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_httpx_mock(self, httpx_mock: HTTPXMock):
        self.httpx_mock = httpx_mock

    async def test_local_resource_success(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ResourceManager("project", "dev", "resource", backend)
            resource = ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="resource",
                product=ResourceProduct.GCP_STORAGE_BUCKET,
                status=ResourceStatus.READY,
                cloud_provider=CloudProvider.GCP,
            )
            await manager.save_resource(resource, "lock_id")

            loaded_resource = await manager.load_resource()
            self.assertEqual(loaded_resource, resource)

    async def test_local_resource_not_found(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ResourceManager("project", "dev", "resource", backend)
            with pytest.raises(exceptions.ResourceNotFound):
                await manager.load_resource()

    async def test_local_resource_delete(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ResourceManager("project", "dev", "resource", backend)
            resource = ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="resource",
                product=ResourceProduct.GCP_STORAGE_BUCKET,
                status=ResourceStatus.READY,
                cloud_provider=CloudProvider.GCP,
            )
            await manager.save_resource(resource, "lock_id")
            # Load environment to ensure it exists
            await manager.load_resource()
            # Delete environment
            await manager.delete_resource("lock_id")
            # Reload the environment to ensure it was deleted
            with pytest.raises(exceptions.ResourceNotFound):
                await manager.load_resource()

    async def test_local_resource_lock(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ResourceManager("project", "dev", "resource", backend)
            lock = await manager.lock_resource(
                operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
            )

            self.assertIsInstance(lock, LocalLock)

            with pytest.raises(exceptions.EntityLocked):
                await lock.acquire()

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_resource_save_success(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = ResourceManager("project", "dev", "resource", backend)
        resource = ResourceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="resource",
            product=ResourceProduct.GCP_STORAGE_BUCKET,
            status=ResourceStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        await manager.save_resource(resource, "lock_id")

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with(
            "prefix/project/dev/resources/resource/flow.state"
        )
        blob_mock.upload_from_string.assert_called_with(
            yaml.dump(resource.to_dict(), sort_keys=False)
        )

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_resource_load_success(self, mock_storage_client):
        resource = ResourceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="resource",
            product=ResourceProduct.GCP_STORAGE_BUCKET,
            status=ResourceStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        def download_as_bytes():
            return yaml.dump(resource.to_dict()).encode("utf-8")

        blob_mock.download_as_bytes = download_as_bytes

        backend = GCSBackend("bucket", "prefix")
        manager = ResourceManager("project", "dev", "resource", backend)
        got = await manager.load_resource()

        assert got == resource

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_resource_load_not_found(self, mock_storage_client):
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
        manager = ResourceManager("project", "dev", "resource", backend)
        with pytest.raises(exceptions.ResourceNotFound):
            await manager.load_resource()

    @mock.patch("launchflow.managers.resource_manager.get_storage_client")
    async def test_gcs_resource_delete(self, mock_storage_client):
        client_mock = mock.MagicMock()
        blob_mock1 = mock.MagicMock(spec=storage.Blob)
        blob_mock2 = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.list_blobs.return_value = [blob_mock1, blob_mock2]

        backend = GCSBackend("bucket", "prefix")
        manager = ResourceManager("project", "dev", "resource", backend)

        await manager.delete_resource("lock_id")

        blob_mock1.delete.assert_called()
        blob_mock2.delete.assert_called()

    @mock.patch("launchflow.locks.get_storage_client")
    async def test_gcs_resource_lock(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = ResourceManager("project", "dev", "resource", backend)

        lock = await manager.lock_resource(
            operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        )

        self.assertIsInstance(lock, GCSLock)

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with(
            "prefix/project/dev/resources/resource/flow.lock"
        )
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
        await lock.release()
        blob_mock.delete.assert_called_once()

    async def test_launchflow_resource_load_success(self):
        resource = ResourceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="resource",
            product=ResourceProduct.GCP_STORAGE_BUCKET,
            status=ResourceStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ResourceManager("project", "dev", "resource", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/resources/resource?account_id=account_id",
            method="GET",
            json=resource.to_dict(),
            match_headers={"Authorization": "Bearer key"},
        )
        got = await manager.load_resource()

        self.assertEqual(got, resource)

    async def test_launchflow_resource_save_success(self):
        resource = ResourceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="resource",
            product=ResourceProduct.GCP_STORAGE_BUCKET,
            status=ResourceStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ResourceManager("project", "dev", "resource", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/resources/resource?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_json=resource.to_dict(),
            match_headers={"Authorization": "Bearer key"},
            json=resource.to_dict(),
        )
        # This just validates that the request is made correctly
        await manager.save_resource(resource, "lock_id")

    async def test_launchflow_resource_load_not_found(self):
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ResourceManager("project", "dev", "resource", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/resources/resource?account_id=account_id",
            method="GET",
            status_code=404,
            match_headers={"Authorization": "Bearer key"},
        )

        with pytest.raises(exceptions.ResourceNotFound):
            await manager.load_resource()

    async def test_launchflow_resource_delete(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/resources/resource?lock_id=lock_id&account_id=account_id",
            method="DELETE",
            match_headers={"Authorization": "Bearer key"},
            json={},
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ResourceManager("project", "dev", "resource", backend)

        await manager.delete_resource("lock_id")

    async def test_launchflow_resource_lock(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/resources/resource/lock?account_id=account_id",
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
            url="https://test.com/v1/projects/project/environments/dev/resources/resource/unlock?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_headers={"Authorization": "Bearer key"},
        )

        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ResourceManager("project", "dev", "resource", backend)

        lock = await manager.lock_resource(
            operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        )

        self.assertIsInstance(lock, LaunchFlowLock)

        await lock.acquire()
        await lock.release()


if __name__ == "__main__":
    unittest.main()
