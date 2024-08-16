import datetime
import tempfile
import unittest
from unittest import mock

import pytest
import yaml
from google.api_core.exceptions import NotFound
from google.cloud import storage
from pytest_httpx import HTTPXMock

from launchflow import exceptions
from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.flow_state import ProjectState


@pytest.mark.usefixtures("launchflow_yaml_remote_backend_fixture")
class ProjectStateManagerTest(unittest.IsolatedAsyncioTestCase):
    # TODO: add tests for list environments
    @pytest.fixture(autouse=True)
    def setup_httpx_mock(self, httpx_mock: HTTPXMock):
        self.httpx_mock = httpx_mock

    async def test_local_project_state_success(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            project_state_manager = ProjectManager("project", backend)
            project_state = ProjectState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="project",
            )
            await project_state_manager.save_project_state(project_state)

            loaded_project_state = await project_state_manager.load_project_state()
            assert loaded_project_state == project_state

    async def test_local_project_state_not_found(self):
        with tempfile.TemporaryDirectory() as tempdir:
            backend = LocalBackend(tempdir)
            project_state_manager = ProjectManager("project", backend)
            with pytest.raises(exceptions.ProjectStateNotFound):
                await project_state_manager.load_project_state()

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_project_state_save_success(self, mock_storage_client):
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        backend = GCSBackend("bucket", "prefix")
        project_state_manager = ProjectManager("project", backend)
        project_state = ProjectState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
        )
        await project_state_manager.save_project_state(project_state)

        client_mock.bucket.assert_called_with("bucket")
        bucket_mock.blob.assert_called_with("prefix/project/flow.state")
        blob_mock.upload_from_string.assert_called_with(
            yaml.dump(project_state.to_dict(), sort_keys=False)
        )

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_project_state_load_success(self, mock_storage_client):
        want_project_state = ProjectState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
        )
        client_mock = mock.MagicMock()
        bucket_mock = mock.MagicMock(spec=storage.Bucket)
        blob_mock = mock.MagicMock(spec=storage.Blob)
        mock_storage_client.return_value = client_mock
        client_mock.bucket.return_value = bucket_mock
        bucket_mock.blob.return_value = blob_mock

        def download_as_bytes():
            return yaml.dump(want_project_state.to_dict()).encode("utf-8")

        blob_mock.download_as_bytes = download_as_bytes

        backend = GCSBackend("bucket", "prefix")
        project_state_manager = ProjectManager("project", backend)
        got = await project_state_manager.load_project_state()

        assert got == want_project_state

    @mock.patch("launchflow.gcp_clients.get_storage_client")
    async def test_gcs_project_state_load_not_found(self, mock_storage_client):
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
        project_state_manager = ProjectManager("project", backend)
        with pytest.raises(exceptions.ProjectStateNotFound):
            await project_state_manager.load_project_state()

    async def test_launchflow_project_state_load_success(self):
        want_project_state = ProjectState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            name="project",
        )
        backend = LaunchFlowBackend(
            lf_cloud_url="https://test.com",
        )
        project_state_manager = ProjectManager("project", backend)
        self.httpx_mock.add_response(
            url="https://test.com/v1/projects/project?account_id=account_id",
            method="GET",
            json=want_project_state.to_dict(),
            match_headers={"Authorization": "Bearer key"},
        )
        got = await project_state_manager.load_project_state()

        self.assertEqual(got, want_project_state)


if __name__ == "__main__":
    unittest.main()
