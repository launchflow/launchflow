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
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.enums import DeploymentProduct, DeploymentStatus
from launchflow.models.flow_state import ServiceState


@pytest.mark.usefixtures("launchflow_yaml_remote_backend_fixture")
class ServiceManagerTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_httpx_mock(self, httpx_mock: HTTPXMock):
        self.httpx_mock = httpx_mock

    async def test_local_service_success(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ServiceManager("project", "dev", "service", backend)
            service = ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="service",
                product=DeploymentProduct.GCP_CLOUD_RUN,
                status=DeploymentStatus.READY,
                cloud_provider=CloudProvider.GCP,
            )
            await manager.save_service(service, "lock_id")

            loaded_service = await manager.load_service()
            self.assertEqual(loaded_service, service)

    async def test_local_service_not_found(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ServiceManager("project", "dev", "service", backend)
            with pytest.raises(exceptions.ServiceNotFound):
                await manager.load_service()

    async def test_local_service_delete(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ServiceManager("project", "dev", "service", backend)
            service = ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="service",
                product=DeploymentProduct.GCP_CLOUD_RUN,
                status=DeploymentStatus.READY,
                cloud_provider=CloudProvider.GCP,
            )
            await manager.save_service(service, "lock_id")
            # Load environment to ensure it exists
            await manager.load_service()
            # Delete environment
            await manager.delete_service("lock_id")
            # Reload the environment to ensure it was deleted
            with pytest.raises(exceptions.ServiceNotFound):
                await manager.load_service()

    async def test_local_service_lock(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            manager = ServiceManager("project", "dev", "service", backend)
            lock = await manager.lock_service(
                operation=LockOperation(operation_type=OperationType.DEPLOY_SERVICE)
            )

            self.assertIsInstance(lock, LocalLock)

            with pytest.raises(exceptions.EntityLocked):
                await lock.acquire()

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_service_save_success(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = ServiceManager("project", "dev", "service", backend)
        service = ServiceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="service",
            product=DeploymentProduct.GCP_CLOUD_RUN,
            status=DeploymentStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        await manager.save_service(service, "lock_id")

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with(
            "prefix/project/dev/services/service/flow.state"
        )
        blob_mock.upload_from_string.assert_called_with(
            yaml.dump(service.to_dict(), sort_keys=False)
        )

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_service_load_success(self, mock_storage_client):
        service = ServiceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="service",
            product=DeploymentProduct.GCP_CLOUD_RUN,
            status=DeploymentStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        def download_as_bytes():
            return yaml.dump(service.to_dict()).encode("utf-8")

        blob_mock.download_as_bytes = download_as_bytes

        backend = GCSBackend("bucket", "prefix")
        manager = ServiceManager("project", "dev", "service", backend)
        got = await manager.load_service()

        assert got == service

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_service_load_not_found(self, mock_storage_client):
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
        manager = ServiceManager("project", "dev", "service", backend)
        with pytest.raises(exceptions.ServiceNotFound):
            await manager.load_service()

    @mock.patch("launchflow.managers.service_manager.get_storage_client")
    async def test_gcs_service_delete(self, mock_storage_client):
        client_mock = mock.MagicMock()
        blob_mock1 = mock.MagicMock(spec=storage.Blob)
        blob_mock2 = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.list_blobs.return_value = [blob_mock1, blob_mock2]

        backend = GCSBackend("bucket", "prefix")
        manager = ServiceManager("project", "dev", "service", backend)

        await manager.delete_service("lock_id")

        blob_mock1.delete.assert_called()
        blob_mock2.delete.assert_called()

    @mock.patch("launchflow.locks.get_storage_client")
    async def test_gcs_service_lock(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        manager = ServiceManager("project", "dev", "service", backend)

        lock = await manager.lock_service(
            operation=LockOperation(operation_type=OperationType.DEPLOY_SERVICE)
        )

        self.assertIsInstance(lock, GCSLock)

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with(
            "prefix/project/dev/services/service/flow.lock"
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
            lock_info.to_dict()
        ).encode("utf-8")

        lock._lock_info = lock_info
        await lock.release()
        blob_mock.delete.assert_called_once()

    async def test_launchflow_service_load_success(self):
        service = ServiceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="service",
            product=DeploymentProduct.GCP_CLOUD_RUN,
            status=DeploymentStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ServiceManager("project", "dev", "service", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/services/service?account_id=account_id",
            method="GET",
            json=service.to_dict(),
            match_headers={"Authorization": "Bearer key"},
        )
        got = await manager.load_service()

        self.assertEqual(got, service)

    async def test_launchflow_service_save_success(self):
        service = ServiceState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="service",
            product=DeploymentProduct.GCP_CLOUD_RUN,
            status=DeploymentStatus.READY,
            cloud_provider=CloudProvider.GCP,
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ServiceManager("project", "dev", "service", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/services/service?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_json=service.to_dict(),
            match_headers={"Authorization": "Bearer key"},
            json=service.to_dict(),
        )
        # This just validates that the request is made correctly
        await manager.save_service(service, "lock_id")

    async def test_launchflow_service_load_not_found(self):
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ServiceManager("project", "dev", "service", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/services/service?account_id=account_id",
            method="GET",
            status_code=404,
            match_headers={"Authorization": "Bearer key"},
        )

        with pytest.raises(exceptions.ServiceNotFound):
            await manager.load_service()

    async def test_launchflow_service_delete(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/services/service?lock_id=lock_id&account_id=account_id",
            method="DELETE",
            match_headers={"Authorization": "Bearer key"},
            json={},
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ServiceManager("project", "dev", "service", backend)

        await manager.delete_service("lock_id")

    async def test_launchflow_service_lock(self):
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project/environments/dev/services/service/lock?account_id=account_id",
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
            url="https://test.com/v1/projects/project/environments/dev/services/service/unlock?lock_id=lock_id&account_id=account_id",
            method="POST",
            match_headers={"Authorization": "Bearer key"},
        )

        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        manager = ServiceManager("project", "dev", "service", backend)

        lock = await manager.lock_service(
            operation=LockOperation(operation_type=OperationType.DEPLOY_SERVICE)
        )

        self.assertIsInstance(lock, LaunchFlowLock)

        await lock.acquire()
        await lock.release()


if __name__ == "__main__":
    unittest.main()
