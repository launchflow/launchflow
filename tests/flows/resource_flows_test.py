import asyncio
import datetime
import unittest
from unittest import mock

import pytest

from launchflow import exceptions
from launchflow.docker.postgres import DockerPostgres
from launchflow.flows import create_flows, resource_flows
from launchflow.gcp import GCSBucket
from launchflow.gcp.cloud_run import CloudRun
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.docker_resource_manager import dict_to_base64
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models.enums import (
    CloudProvider,
    EnvironmentStatus,
    EnvironmentType,
    ResourceProduct,
    ResourceStatus,
    ServiceProduct,
    ServiceStatus,
)
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
    ResourceState,
    ServiceState,
)
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.workflows.apply_resource_tofu.schemas import ApplyResourceTofuOutputs
from launchflow.workflows.destroy_resource_tofu.schemas import DestroyResourceTofuInputs
from launchflow.workflows.manage_docker.schemas import DestroyResourceDockerInputs


# Define the mock datetime class
class MockDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class ResourceFlowTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_capsys(self, capsys):
        self.capsys = capsys

    async def asyncSetUp(self):
        self.backend = self.launchflow_yaml.backend
        # Patch the docker service check, otherwise, docker has to be running in the test environment
        self.docker_service_available = mock.patch(
            "launchflow.flows.resource_flows.docker_service_available",
            return_value=True,
        )
        self._mock_docker_service_available = self.docker_service_available.start()

        self.environment_manager = EnvironmentManager(
            backend=self.backend, project_name="unittest", environment_name="dev"
        )
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
        await self.environment_manager.save_environment(
            environment_state=self.environment, lock_id="lock"
        )

    async def asyncTearDown(self):
        self.docker_service_available.stop()

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_new_bucket(self, mock_create_resource: mock.AsyncMock):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        await create_flows.create(resource, environment="dev", prompt=False)

        mock_create_resource.assert_called_once_with(
            tofu_resource=resource,
            environment_state=self.environment,
            backend=self.backend,
            launchflow_uri=LaunchFlowURI(
                project_name="unittest",
                environment_name="dev",
                resource_name="test-storage-bucket",
                service_name=None,
            ),
            lock_id=mock.ANY,
            logs_file=mock.ANY,
        )

        manager = self.environment_manager.create_resource_manager(mock_resource_name)
        resource_state = await manager.load_resource()
        self.assertEqual(
            resource_state,
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-storage-bucket",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_bucket_failure(self, mock_create_resource: mock.AsyncMock):
        """Checks that the lock is released even if an exception is raised."""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)

        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)
        mock_create_resource.side_effect = ValueError("this failed")

        await create_flows.create(resource, environment="dev", prompt=False)

        rm = self.environment_manager.create_resource_manager(mock_resource_name)
        resource_state = await rm.load_resource()
        # Verify that the resource is not ready
        self.assertEqual(
            resource_state,
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs=None,
                status=ResourceStatus.CREATE_FAILED,
                gcp_id=None,
                aws_arn=None,
            ),
        )
        # verify that we can aquire the lock again, this ensures
        # that the lock was released
        lock = await rm.lock_resource(
            operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        )
        await lock.release()

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_already_exists(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Test no-op bucket creation cause it already exists."""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        rm = self.environment_manager.create_resource_manager(mock_resource_name)
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-storage-bucket",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        await create_flows.create(resource, environment="dev", prompt=False)

        mock_create_resource.assert_not_called()

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_update_bucket(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Test create updating an existing bucket."""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name, location="EU")
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket2",
            aws_arn="arn2",
        )

        rm = self.environment_manager.create_resource_manager(mock_resource_name)
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        await create_flows.create(resource, environment="dev", prompt=False)

        mock_create_resource.assert_called_once_with(
            tofu_resource=resource,
            environment_state=self.environment,
            backend=self.backend,
            launchflow_uri=LaunchFlowURI(
                project_name="unittest",
                environment_name="dev",
                resource_name="test-storage-bucket",
                service_name=None,
            ),
            lock_id=mock.ANY,
            logs_file=mock.ANY,
        )

        manager = self.environment_manager.create_resource_manager(mock_resource_name)
        resource_state = await manager.load_resource()
        self.assertEqual(
            resource_state,
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "resource_id": "test-storage-bucket",
                    "location": "EU",
                    "force_destroy": "false",
                },
                status=ResourceStatus.READY,
                aws_arn="arn2",
                gcp_id="bucket2",
            ),
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_environment_locked(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Test that we can't create a resource when the environment is locked"""

        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)

        async with await self.environment_manager.lock_environment(
            operation=LockOperation(operation_type=OperationType.CREATE_ENVIRONMENT)
        ):
            with self.assertRaises(exceptions.FailedToLockPlans):
                await create_flows.create(resource, environment="dev", prompt=False)
        mock_create_resource.assert_not_called()

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_resource_locked(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Test that we can't create a locked resource"""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)

        rm = self.environment_manager.create_resource_manager(mock_resource_name)
        async with await rm.lock_resource(
            operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        ):
            with self.assertRaises(exceptions.FailedToLockPlans):
                await create_flows.create(resource, environment="dev", prompt=False)
        mock_create_resource.assert_not_called()

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_lock_resource_during_creation(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Test that the lock is held during resource creation."""
        mock_resource_name = "test-storage-bucket"
        resource = GCSBucket(mock_resource_name)

        async def slow_mock(*args, **kwargs):
            await asyncio.sleep(5)

        mock_create_resource.side_effect = slow_mock

        task = asyncio.create_task(
            create_flows.create(resource, environment="dev", prompt=False)
        )

        # Wait for the lock to be held
        await asyncio.sleep(0.1)
        rm = self.environment_manager.create_resource_manager(mock_resource_name)

        with self.assertRaises(exceptions.EntityLocked):
            async with await rm.lock_resource(
                operation=LockOperation(operation_type=OperationType.CREATE_RESOURCE)
            ):
                pass
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_mock_bucket(
        self,
        mock_delete_resource: mock.AsyncMock,
    ):
        """Nomimal case, destroys a bucket with mocking."""

        rm = self.environment_manager.create_resource_manager("bucket")
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        result = await resource_flows.destroy("dev", prompt=False)
        assert result
        mock_delete_resource.assert_called_once_with(
            DestroyResourceTofuInputs(
                launchflow_uri=LaunchFlowURI(
                    project_name="unittest",
                    environment_name="dev",
                    resource_name="bucket",
                    service_name=None,
                ),
                backend=self.backend,
                gcp_env_config=self.environment.gcp_config,
                aws_env_config=self.environment.aws_config,
                resource=ResourceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name="test-storage-bucket",
                    cloud_provider=CloudProvider.GCP,
                    product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                    gcp_id="bucket",
                    aws_arn="arn",
                    inputs={"location": "US", "force_destroy": "false"},
                    status=ResourceStatus.DESTROYING,
                ),
                lock_id=mock.ANY,
                logs_file=mock.ANY,
            )
        )

        with self.assertRaises(exceptions.ResourceNotFound):
            await rm.load_resource()

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_mock_bucket_failed(
        self,
        mock_delete_resource: mock.AsyncMock,
    ):
        """Nomimal case, destroys a bucket with mocking."""

        rm = self.environment_manager.create_resource_manager("bucket")
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        mock_delete_resource.side_effect = ValueError("this failed")

        result = await resource_flows.destroy("dev", prompt=False)
        assert not result
        resource = await rm.load_resource()
        self.assertEqual(resource.status, ResourceStatus.DELETE_FAILED)

    @mock.patch("launchflow.flows.resource_flows.destroy_docker_resource")
    @mock.patch("launchflow.clients.docker_client.docker.from_env")
    async def test_destroy_local_resource(
        self,
        mock_from_env: mock.AsyncMock,
        mock_destroy_docker_resource: mock.AsyncMock,
    ):
        """Nominal case, local resource destroy."""
        mock_container_id = "mock_container_id"
        mock_docker_client = mock_from_env.return_value
        mock_docker_client.containers.list.return_value = [
            mock.Mock(
                status="running",
                id=mock_container_id,
                labels={
                    "launchflow_managed": "true",
                    "environment": "dev",
                    "resource": "docker_resource",
                    "inputs": None,
                },
                attrs={"Created": datetime.datetime.now()},
            )
        ]
        await resource_flows.destroy("dev", local_only=True, prompt=False)

        self.assertEqual(1, mock_destroy_docker_resource.call_count)

        call_args = mock_destroy_docker_resource.call_args_list[0][0]
        self.assertEqual(1, len(call_args))
        self.assertIsInstance(call_args[0], DestroyResourceDockerInputs)
        self.assertEqual(mock_container_id, call_args[0].container_id)

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_with_node_filter(self, mock_delete_tofu_resource: mock.Mock):
        """Test that destroy with a Node filter works."""

        resources = []
        for ind in range(2):
            name = f"test-bucket{ind}"
            rm = self.environment_manager.create_resource_manager(name)
            await rm.save_resource(
                ResourceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=name,
                    cloud_provider=CloudProvider.GCP,
                    product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                    inputs={"location": "US", "force_destroy": "false"},
                    status=ResourceStatus.READY,
                    aws_arn="arn",
                    gcp_id="bucket",
                ),
                "test",
            )

            resources.append(GCSBucket(name))

        await resource_flows.destroy("dev", resources[0], prompt=False)

        with self.assertRaises(exceptions.ResourceNotFound):
            _ = await self.environment_manager.create_resource_manager(
                resources[0].name
            ).load_resource()

        resource1_state = await self.environment_manager.create_resource_manager(
            resources[1].name
        ).load_resource()
        self.assertEqual(resource1_state.status, ResourceStatus.READY)

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_with_resource_filter(
        self, mock_delete_tofu_resource: mock.Mock
    ):
        """Test that destroy with a resource name filter works."""

        resources = []
        services = []
        for ind in range(2):
            name = f"test-bucket{ind}"
            rm = self.environment_manager.create_resource_manager(name)
            await rm.save_resource(
                ResourceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=name,
                    cloud_provider=CloudProvider.GCP,
                    product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                    inputs={"location": "US", "force_destroy": "false"},
                    status=ResourceStatus.READY,
                    aws_arn="arn",
                    gcp_id="bucket",
                ),
                "test",
            )

            resources.append(GCSBucket(name))

        for ind in range(2):
            name = f"test-service{ind}"
            sm = self.environment_manager.create_service_manager(name)
            await sm.save_service(
                ServiceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=name,
                    cloud_provider=CloudProvider.GCP,
                    product=ServiceProduct.GCP_CLOUD_RUN,
                    inputs={},
                    status=ServiceStatus.READY,
                    aws_arn="arn",
                    gcp_id="bucket",
                    docker_image="gcr.io/project/image",
                    service_url="https://service-url",
                ),
                "test",
            )

            services.append(CloudRun(name))

        await resource_flows.destroy(
            "dev", resources_to_destroy=set([resources[0].name]), prompt=False
        )

        with self.assertRaises(exceptions.ResourceNotFound):
            _ = await self.environment_manager.create_resource_manager(
                resources[0].name
            ).load_resource()

        # The service should still exist
        service = await self.environment_manager.create_service_manager(
            services[0].name
        ).load_service()
        self.assertEqual(service.product, ServiceProduct.GCP_CLOUD_RUN)

        resource1_state = await self.environment_manager.create_resource_manager(
            resources[1].name
        ).load_resource()
        self.assertEqual(resource1_state.status, ResourceStatus.READY)

    async def test_destroy_with_service_filter(self):
        """Test that destroy with a service name filter works."""

        services = []
        for ind in range(2):
            name = f"test-service{ind}"
            sm = self.environment_manager.create_service_manager(name)
            await sm.save_service(
                ServiceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=name,
                    cloud_provider=CloudProvider.GCP,
                    product=ServiceProduct.GCP_CLOUD_RUN,
                    inputs={},
                    status=ServiceStatus.READY,
                    aws_arn=None,
                    gcp_id="service-id",
                    docker_image="gcr.io/project/image",
                    service_url="https://service-url",
                ),
                "test",
            )

            services.append(CloudRun(name))

        await resource_flows.destroy(
            "dev", services_to_destroy=set([services[0].name]), prompt=False
        )

        with self.assertRaises(exceptions.ServiceNotFound):
            _ = await self.environment_manager.create_service_manager(
                services[0].name
            ).load_service()

        service1_state = await self.environment_manager.create_service_manager(
            services[1].name
        ).load_service()
        self.assertEqual(service1_state.status, ServiceStatus.READY)

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_with_node_and_resource_and_service_filter(
        self,
        mock_delete_tofu_resource: mock.Mock,
    ):
        """Test that destroy with a service name filter works."""

        resources = []
        services = []
        for ind in range(3):
            service_name = f"test-service{ind}"
            sm = self.environment_manager.create_service_manager(service_name)
            await sm.save_service(
                ServiceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=service_name,
                    cloud_provider=CloudProvider.GCP,
                    product=ServiceProduct.GCP_CLOUD_RUN,
                    inputs={},
                    status=ServiceStatus.READY,
                    aws_arn=None,
                    gcp_id="service-id",
                    docker_image="gcr.io/project/image",
                    service_url="https://service-url",
                ),
                "test",
            )
            services.append(CloudRun(service_name))

            resource_name = f"test-bucket{ind}"
            rm = self.environment_manager.create_resource_manager(resource_name)
            await rm.save_resource(
                ResourceState(
                    created_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    updated_at=datetime.datetime(
                        2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    name=resource_name,
                    cloud_provider=CloudProvider.GCP,
                    product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                    inputs={"location": "US", "force_destroy": "false"},
                    status=ResourceStatus.READY,
                    aws_arn="arn",
                    gcp_id="bucket",
                ),
                "test",
            )
            resources.append(GCSBucket(resource_name))

        # We pass in the first 2 resources / services to destroy, then filter out the
        # first one so only the second should be destroyed
        # TLDR: node fitler should filter out #3, other filters should filter out #2,
        # only #1 should be destroyed
        await resource_flows.destroy(
            "dev",
            resources[0],
            resources[1],
            services[0],
            services[1],
            resources_to_destroy=set([resources[0].name]),
            services_to_destroy=set([services[0].name]),
            prompt=False,
        )

        # test final resource states
        with self.assertRaises(exceptions.ResourceNotFound):
            _ = await self.environment_manager.create_resource_manager(
                resources[0].name
            ).load_resource()

        resource1_state = await self.environment_manager.create_resource_manager(
            resources[1].name
        ).load_resource()
        self.assertEqual(resource1_state.status, ResourceStatus.READY)
        resource2_state = await self.environment_manager.create_resource_manager(
            resources[2].name
        ).load_resource()
        self.assertEqual(resource2_state.status, ResourceStatus.READY)

        # Test final service states
        with self.assertRaises(exceptions.ServiceNotFound):
            _ = await self.environment_manager.create_service_manager(
                services[0].name
            ).load_service()

        service1_state = await self.environment_manager.create_service_manager(
            services[1].name
        ).load_service()
        self.assertEqual(service1_state.status, ServiceStatus.READY)
        service2_state = await self.environment_manager.create_service_manager(
            services[2].name
        ).load_service()
        self.assertEqual(service2_state.status, ServiceStatus.READY)

    async def test_destroy_nonexistant_resource(self):
        """Test that destroying a non-existant resource raises an exception."""
        mock_resource = GCSBucket("test-bucket")
        with self.assertRaises(exceptions.ResourceNotFound):
            await resource_flows.destroy("dev", mock_resource, prompt=False)

    async def test_destroy_gcp_service_successful(self):
        service_manager = self.environment_manager.create_service_manager("gcp-service")
        await service_manager.save_service(
            ServiceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="gcp-service",
                cloud_provider=CloudProvider.GCP,
                product=ServiceProduct.GCP_CLOUD_RUN,
                inputs={},
                status=ServiceStatus.READY,
                aws_arn=None,
                service_url="https://service-url",
                docker_image="gcr.io/project/image",
                gcp_id="service-id",
            ),
            "test",
        )

        result = await resource_flows.destroy("dev", prompt=False)
        assert result

        with self.assertRaises(exceptions.ServiceNotFound):
            await service_manager.load_service()

    async def test_destroy_aws_service_successful(self):
        service_manager = self.environment_manager.create_service_manager("aws-service")
        await service_manager.save_service(
            ServiceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="aws-service",
                cloud_provider=CloudProvider.AWS,
                product=ServiceProduct.AWS_ECS_FARGATE,
                inputs={},
                status=ServiceStatus.READY,
                gcp_id=None,
                service_url="https://service-url",
                docker_image="ecr.io/project/image",
                aws_arn="service-arn",
            ),
            "test",
        )

        await resource_flows.destroy("dev", prompt=False)

        with self.assertRaises(exceptions.ServiceNotFound):
            await service_manager.load_service()

    async def test_plan_resources_update_bucket(self):
        bucket = GCSBucket("test-bucket", force_destroy=True)

        rm = self.environment_manager.create_resource_manager("test-bucket")
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="test-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-bucket",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test-bucket",
        )

        plans = await create_flows.plan_create(
            bucket,
            environment_state=self.environment,
            environment_manager=self.environment_manager,
            verbose=False,
        )

        self.assertEqual(len(plans), 1)
        self.assertIsInstance(plans[0], create_flows.CreateResourcePlan)
        self.assertEqual(plans[0].resource.name, "test-bucket")
        self.assertEqual(plans[0].operation_type, "update")

    async def test_plan_resources_replace_bucket(self):
        bucket = GCSBucket("test-bucket", location="EU")

        rm = self.environment_manager.create_resource_manager("test-bucket")
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name="test-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test-bucket",
        )

        plans = await create_flows.plan_create(
            bucket,
            environment_state=self.environment,
            environment_manager=self.environment_manager,
            verbose=False,
        )

        self.assertEqual(len(plans), 1)
        self.assertIsInstance(plans[0], create_flows.CreateResourcePlan)
        self.assertEqual(plans[0].resource.name, "test-bucket")
        self.assertEqual(plans[0].operation_type, "replace")

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_with_deps(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        resource2.depends_on(resource1)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        await create_flows.create(resource1, resource2, environment="dev", prompt=False)

        # Verify that the calls are in order
        mock_create_resource.assert_has_calls(
            [
                mock.call(
                    tofu_resource=resource1,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket1",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource2,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket2",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
            ]
        )

        manager = self.environment_manager.create_resource_manager(mock_resource_name2)
        resource_state = await manager.load_resource()
        self.assertEqual(
            resource_state,
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket2",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-storage-bucket2",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
                depends_on=["test-storage-bucket1"],
            ),
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_multi_parents(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        mock_resource_name3 = "test-storage-bucket3"
        resource3 = GCSBucket(mock_resource_name3)
        resource3.depends_on(resource1, resource2)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        await create_flows.create(
            resource1, resource2, resource3, environment="dev", prompt=False
        )

        # Verify that the calls are in order
        mock_create_resource.assert_has_calls(
            [
                mock.call(
                    tofu_resource=resource1,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket1",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource2,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket2",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource3,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket3",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
            ]
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_parent_doesnt_exist(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        resource2.depends_on(resource1)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )
        await create_flows.create(resource2, environment="dev", prompt=False)

        # This shouldn't be called since the parent dependencies don't exist
        mock_create_resource.assert_not_called()

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_parent_already_exist(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        resource2.depends_on(resource1)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        rm = self.environment_manager.create_resource_manager(mock_resource_name1)
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket1",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-storage-bucket1",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        await create_flows.create(resource2, environment="dev", prompt=False)

        # This shouldn't be called since the parent dependencies don't exist
        mock_create_resource.assert_called_once_with(
            tofu_resource=resource2,
            environment_state=self.environment,
            backend=self.backend,
            launchflow_uri=LaunchFlowURI(
                project_name="unittest",
                environment_name="dev",
                resource_name="test-storage-bucket2",
                service_name=None,
            ),
            lock_id=mock.ANY,
            logs_file=mock.ANY,
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_one_parent_already_exist(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        mock_resource_name3 = "test-storage-bucket3"
        resource3 = GCSBucket(mock_resource_name3)
        resource3.depends_on(resource1, resource2)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        rm = self.environment_manager.create_resource_manager(mock_resource_name1)
        await rm.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket1",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={
                    "location": "US",
                    "force_destroy": "false",
                    "resource_id": "test-storage-bucket1",
                },
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )

        await create_flows.create(resource2, resource3, environment="dev", prompt=False)

        # This shouldn't be called since the parent dependencies don't exist
        mock_create_resource.assert_has_calls(
            [
                mock.call(
                    tofu_resource=resource2,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket2",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource3,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket3",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
            ]
        )

    @mock.patch("datetime.datetime", MockDateTime)
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_mock_bucket_multi_parent_levels(
        self, mock_create_resource: mock.AsyncMock
    ):
        """Nomimal case, creates a GCS bucket with mocking."""
        mock_resource_name1 = "test-storage-bucket1"
        resource1 = GCSBucket(mock_resource_name1)
        mock_resource_name2 = "test-storage-bucket2"
        resource2 = GCSBucket(mock_resource_name2)
        resource2.depends_on(resource1)
        mock_resource_name3 = "test-storage-bucket3"
        resource3 = GCSBucket(mock_resource_name3)
        resource3.depends_on(resource2)
        mock_create_resource.return_value = ApplyResourceTofuOutputs(
            # In practice these won't both be returned but we might as well
            # test it
            gcp_id="bucket",
            aws_arn="arn",
        )

        await create_flows.create(
            resource1, resource2, resource3, environment="dev", prompt=False
        )

        # Verify that the calls are in order
        mock_create_resource.assert_has_calls(
            [
                mock.call(
                    tofu_resource=resource1,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket1",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource2,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket2",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
                mock.call(
                    tofu_resource=resource3,
                    environment_state=self.environment,
                    backend=self.backend,
                    launchflow_uri=LaunchFlowURI(
                        project_name="unittest",
                        environment_name="dev",
                        resource_name="test-storage-bucket3",
                        service_name=None,
                    ),
                    lock_id=mock.ANY,
                    logs_file=mock.ANY,
                ),
            ]
        )

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    async def test_create_and_destroy_no_docker(
        self, mock_create: mock.AsyncMock, mock_destroy: mock.AsyncMock
    ):
        """Test that creating and destroying resources raise when Docker is not available."""
        with mock.patch(
            "launchflow.flows.create_flows.docker_service_available",
            return_value=False,
        ) as mock_is_docker_available_in_create:
            with mock.patch(
                "launchflow.flows.resource_flows.docker_service_available",
                return_value=False,
            ) as mock_is_docker_available_in_resource:
                await create_flows.create(
                    DockerPostgres("test-postgres"), environment="dev"
                )

                with self.assertRaises(exceptions.MissingDockerDependency):
                    await resource_flows.destroy(
                        "dev", DockerPostgres("test-postgres"), local_only=True
                    )

                with self.assertRaises(exceptions.MissingDockerDependency):
                    await resource_flows.destroy("dev", DockerPostgres("test-postgres"))

                mock_create.assert_not_called()
                mock_destroy.assert_not_called()

                self.assertEqual(1, mock_is_docker_available_in_create.call_count)
                self.assertEqual(2, mock_is_docker_available_in_resource.call_count)

    @mock.patch(
        "launchflow.workflows.manage_docker.manage_docker_resources.find_open_port"
    )
    @mock.patch("launchflow.clients.docker_client.docker.from_env")
    async def test_create_docker_resource_create(
        self, mock_from_env: mock.AsyncMock, mock_find_open_port: mock.Mock
    ):
        """Nominal case, creates a docker postgres resource."""
        mock_open_port = 12345
        mock_find_open_port.return_value = mock_open_port
        mock_docker_client = mock_from_env.return_value

        resource = DockerPostgres("test-docker-postgres")

        mock_docker_client.containers.list.return_value = []
        await create_flows.create(resource, environment="dev", prompt=False)
        mock_docker_client.containers.list.return_value = [
            mock.Mock(
                status="running",
                id="mock_container_id",
                labels={
                    "launchflow_managed": "true",
                    "environment": "dev",
                    "resource": "test-docker-postgres",
                    "inputs": dict_to_base64(
                        {"password": "password", "ports": {"5432/tcp": mock_open_port}}
                    ),
                },
                attrs={"Created": datetime.datetime.now()},
            )
        ]
        await create_flows.create(resource, environment="dev", prompt=False)

        # Calling the create twice should only call the docker client once, since no changes are made
        self.assertEqual(1, mock_docker_client.containers.run.call_count)

    @mock.patch(
        "launchflow.workflows.manage_docker.manage_docker_resources.find_open_port"
    )
    @mock.patch("launchflow.clients.docker_client.docker.from_env")
    async def test_create_docker_resource_create_then_update(
        self, mock_from_env: mock.Mock, mock_find_open_port: mock.Mock
    ):
        """Checks that creating a docker postgres resource, then updating it works as expected."""
        mock_open_port = 12345
        mock_find_open_port.return_value = mock_open_port
        mock_docker_client = mock_from_env.return_value

        resource = DockerPostgres("test-docker-postgres")

        mock_docker_client.containers.list.return_value = []
        await create_flows.create(resource, environment="dev", prompt=False)
        mock_docker_client.containers.list.return_value = [
            mock.Mock(
                status="running",
                id="mock_container_id",
                labels={
                    "launchflow_managed": "true",
                    "environment": "dev",
                    "resource": "test-docker-postgres",
                    "inputs": dict_to_base64(
                        {
                            "password": "password",
                            "ports": {"5432/tcp": mock_open_port + 1},
                        }
                    ),
                },
                attrs={"Created": datetime.datetime.now()},
            )
        ]
        await create_flows.create(resource, environment="dev", prompt=False)

        # Calling the create twice should only call the docker client once, since no changes are made
        self.assertEqual(2, mock_docker_client.containers.run.call_count)

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_mock_bucket_with_deps(
        self,
        mock_delete_resource: mock.AsyncMock,
    ):
        """Nomimal case, destroys a bucket with mocking."""

        rm1 = self.environment_manager.create_resource_manager("test-storage-bucket")
        await rm1.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )
        rm2 = self.environment_manager.create_resource_manager("test-storage-bucket2")
        await rm2.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket2",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
                depends_on=["test-storage-bucket"],
            ),
            "test",
        )

        await resource_flows.destroy("dev", prompt=False)

        mock_delete_resource.assert_has_calls(
            [
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket2",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket2",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                            depends_on=["test-storage-bucket"],
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
            ]
        )

        with self.assertRaises(exceptions.ResourceNotFound):
            await rm1.load_resource()
        with self.assertRaises(exceptions.ResourceNotFound):
            await rm2.load_resource()

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_mock_bucket_with_multiple_deps(
        self,
        mock_delete_resource: mock.AsyncMock,
    ):
        """Nomimal case, destroys a bucket with mocking."""

        rm1 = self.environment_manager.create_resource_manager("test-storage-bucket")
        await rm1.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )
        rm2 = self.environment_manager.create_resource_manager("test-storage-bucket2")
        await rm2.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket2",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )
        rm3 = self.environment_manager.create_resource_manager("test-storage-bucket3")
        await rm3.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket3",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
                depends_on=["test-storage-bucket", "test-storage-bucket2"],
            ),
            "test",
        )

        await resource_flows.destroy("dev", prompt=False)

        mock_delete_resource.assert_has_calls(
            [
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket3",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket3",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                            depends_on=["test-storage-bucket", "test-storage-bucket2"],
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket2",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket2",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
            ]
        )

        with self.assertRaises(exceptions.ResourceNotFound):
            await rm1.load_resource()
        with self.assertRaises(exceptions.ResourceNotFound):
            await rm2.load_resource()
        with self.assertRaises(exceptions.ResourceNotFound):
            await rm3.load_resource()

    @mock.patch("launchflow.flows.resource_flows.delete_tofu_resource")
    async def test_destroy_mock_bucket_with_multiple_level_deps(
        self,
        mock_delete_resource: mock.AsyncMock,
    ):
        """Nomimal case, destroys a bucket with mocking."""

        rm1 = self.environment_manager.create_resource_manager("test-storage-bucket")
        await rm1.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
            ),
            "test",
        )
        rm2 = self.environment_manager.create_resource_manager("test-storage-bucket2")
        await rm2.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket2",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
                depends_on=["test-storage-bucket"],
            ),
            "test",
        )
        rm3 = self.environment_manager.create_resource_manager("test-storage-bucket3")
        await rm3.save_resource(
            ResourceState(
                created_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                updated_at=datetime.datetime(
                    2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
                name="test-storage-bucket3",
                cloud_provider=CloudProvider.GCP,
                product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                inputs={"location": "US", "force_destroy": "false"},
                status=ResourceStatus.READY,
                aws_arn="arn",
                gcp_id="bucket",
                depends_on=["test-storage-bucket2"],
            ),
            "test",
        )

        await resource_flows.destroy("dev", prompt=False)

        mock_delete_resource.assert_has_calls(
            [
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket3",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket3",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                            depends_on=["test-storage-bucket2"],
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket2",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket2",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                            depends_on=["test-storage-bucket"],
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
                mock.call(
                    DestroyResourceTofuInputs(
                        launchflow_uri=LaunchFlowURI(
                            project_name="unittest",
                            environment_name="dev",
                            resource_name="test-storage-bucket",
                            service_name=None,
                        ),
                        backend=self.backend,
                        gcp_env_config=self.environment.gcp_config,
                        aws_env_config=self.environment.aws_config,
                        resource=ResourceState(
                            created_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            updated_at=datetime.datetime(
                                2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                            ),
                            name="test-storage-bucket",
                            cloud_provider=CloudProvider.GCP,
                            product=ResourceProduct.GCP_STORAGE_BUCKET.value,
                            gcp_id="bucket",
                            aws_arn="arn",
                            inputs={"location": "US", "force_destroy": "false"},
                            status=ResourceStatus.DESTROYING,
                        ),
                        lock_id=mock.ANY,
                        logs_file=mock.ANY,
                    )
                ),
            ]
        )

        with self.assertRaises(exceptions.ResourceNotFound):
            await rm1.load_resource()
        with self.assertRaises(exceptions.ResourceNotFound):
            await rm2.load_resource()

    async def test_force_unlock_resource_success(self):
        resource_manager = self.environment_manager.create_resource_manager(
            "test-resource"
        )

        # Lock the resource
        lock = await resource_manager.lock_resource(
            LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        )

        # Force unlock the resource
        await resource_manager.force_unlock_resource()

        # Try to lock the resource again to ensure it's unlocked
        lock = await resource_manager.lock_resource(
            LockOperation(operation_type=OperationType.CREATE_RESOURCE)
        )
        await lock.release()

    async def test_force_unlock_resource_not_locked(self):
        resource_manager = self.environment_manager.create_resource_manager(
            "test-resource"
        )

        with self.assertRaises(exceptions.LockNotFound):
            await resource_manager.force_unlock_resource()


if __name__ == "__main__":
    unittest.main()
