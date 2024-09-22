import datetime
import tempfile
import unittest
from unittest import mock

import pytest

from launchflow import exceptions
from launchflow.aws.ecs_fargate import ECSFargateService
from launchflow.aws.lambda_service import LambdaService
from launchflow.aws.service import AWSService
from launchflow.flows import deploy_flows
from launchflow.gcp.cloud_run import CloudRunService
from launchflow.gcp.service import GCPService
from launchflow.locks import LockOperation, OperationType
from launchflow.logger import logger
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models import enums, flow_state
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.service import ServiceOutputs
from launchflow.workflows.apply_resource_tofu.schemas import ApplyResourceTofuOutputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class DeployFlowsTest(unittest.IsolatedAsyncioTestCase):
    @pytest.fixture(autouse=True)
    def setup_capsys(self, capsys):
        self.capsys = capsys

    async def asyncSetUp(self):
        self.backend = self.launchflow_yaml.backend
        self.dev_environment_manager = EnvironmentManager(
            project_name=self.launchflow_yaml.project,
            environment_name=self.launchflow_yaml.default_environment,
            backend=self.backend,
        )
        self.dev_environment = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="test-account",
                region="us-west-2",
                iam_role_arn="test-arn",
                vpc_id="test-vpc",
                artifact_bucket="test-bucket",
            ),
        )
        await self.dev_environment_manager.save_environment(
            environment_state=self.dev_environment, lock_id="lock"
        )

        self.prod_environment_manager = EnvironmentManager(
            project_name="unittest",
            environment_name="prod",
            backend=self.backend,
        )
        self.prod_environment = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            environment_type=enums.EnvironmentType.PRODUCTION,
            gcp_config=flow_state.GCPEnvironmentConfig(
                project_id="test-project-prod",
                default_region="us-central1",
                default_zone="us-central1-a",
                service_account_email="test-email",
                artifact_bucket="test-bucket",
            ),
            aws_config=flow_state.AWSEnvironmentConfig(
                account_id="test-account",
                region="us-west-2",
                iam_role_arn="test-arn",
                vpc_id="test-vpc-prod",
                artifact_bucket="test-bucket",
            ),
        )
        await self.prod_environment_manager.save_environment(
            environment_state=self.prod_environment, lock_id="lock"
        )

        logger.setLevel("DEBUG")

    async def test_deploy_gcp_service_no_environment(self):
        service = CloudRunService("my-gcp-service")
        with pytest.raises(exceptions.EnvironmentNotFound):
            await deploy_flows.deploy(
                service, environment="does-not-exist", prompt=False
            )

    async def test_deploy_aws_service_no_environment(self):
        service = ECSFargateService("my-aws-service")
        with pytest.raises(exceptions.EnvironmentNotFound):
            await deploy_flows.deploy(
                service, environment="does-not-exist", prompt=False
            )

    async def test_deploy_gcp_service_no_gcp_config(self):
        service = CloudRunService("my-gcp-service")
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="no-gcp-config",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            gcp_config=None,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        result = await deploy_flows.deploy(
            service, environment="no-gcp-config", prompt=False
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.failed_plans), 1)
        self.assertIn("CloudProviderMismatch", result.failed_plans[0].error_message)

    async def test_deploy_aws_service_no_aws_config(self):
        service = ECSFargateService("my-aws-service")
        manager = EnvironmentManager(
            project_name="unittest",
            environment_name="no-aws-config",
            backend=self.backend,
        )
        env = flow_state.EnvironmentState(
            created_at=datetime.datetime(2021, 1, 1),
            updated_at=datetime.datetime(2021, 1, 1),
            environment_type=enums.EnvironmentType.DEVELOPMENT,
            aws_config=None,
        )
        await manager.save_environment(environment_state=env, lock_id="lock")
        result = await deploy_flows.deploy(
            service, environment="no-aws-config", prompt=False
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.failed_plans), 1)
        self.assertIn("CloudProviderMismatch", result.failed_plans[0].error_message)

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_cloud_run_successful(
        self,
        time_mock,
        uuid_mock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        # Setup the deploy service mock
        build_mock = mock.AsyncMock(return_value="gcr.io/project/service:latest")
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            service = GCPService("my-gcp-service", build_directory=tmpdirname)

            service.build = build_mock
            service.release = release_mock
            service.inputs = mock.Mock(return_value=Inputs())
            service.outputs = mock.Mock(return_value=service_outputs)
            service.resources = mock.Mock(return_value=[])

            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=True,
            )
            self.assertTrue(result.success)

        deployment_id = "1640995200000"
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        launchflow_uri = LaunchFlowURI(
            project_name=self.launchflow_yaml.project,
            environment_name=self.launchflow_yaml.default_environment,
            service_name="my-gcp-service",
        )
        build_mock.assert_called_once_with(
            environment_state=self.dev_environment,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            build_log_file=mock.ANY,
            build_local=True,
        )
        release_mock.assert_called_once_with(
            release_inputs="gcr.io/project/service:latest",
            environment_state=self.dev_environment,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            release_log_file=mock.ANY,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.UNKNOWN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.deployment_id, deployment_id)
        self.assertEqual(got_service.service_url, "https://service-1234-uc.a.run.app")
        self.assertEqual(got_service.gcp_id, "service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)
        # Make sure the docker_image is no longer set
        self.assertEqual(got_service.docker_image, None)

    # TODO: Add a test that mocks out steps in the workflow, to handle branching logic between deploy and promote
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_service_build_failure(
        self,
        time_mock,
        uuid_mock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        # Simulate a failure during the build step
        build_mock = mock.AsyncMock(side_effect=exceptions.MissingAWSDependency())
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        # Call the deploy service flow with the build_local flag off and verify the inputs / outputs
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            service = GCPService("my-gcp-service", build_directory=tmpdirname)

            service.build = build_mock
            service.release = release_mock
            service.inputs = mock.Mock(return_value=Inputs())
            service.outputs = mock.Mock(return_value=service_outputs)
            service.resources = mock.Mock(return_value=[])

            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=False,
            )
            self.assertFalse(result.success)

        # Ensure the release step is not called
        release_mock.assert_not_called()

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.UNKNOWN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.gcp_id, "service-1234")
        # NOTE: only deployment_id and service url are None since the create step was successful
        self.assertEqual(got_service.deployment_id, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.DEPLOY_FAILED)

    # TODO: Add tests for the promote flow once AWSServices support promotion
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_aws_service_successful(
        self,
        time_mock,
        uuid_mock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id=None,
            aws_arn="service-1234",
        )
        # Setup the deploy service mocks
        build_mock = mock.AsyncMock(return_value="ecr.io/project/service:latest")
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")

            service = AWSService("my-aws-service", build_directory=tmpdirname)

            service.build = build_mock
            service.release = release_mock
            service.inputs = mock.Mock(return_value=Inputs())
            service.outputs = mock.Mock(return_value=service_outputs)
            service.resources = mock.Mock(return_value=[])

            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=True,
            )
            self.assertTrue(result.success)

        deployment_id = "1640995200000"
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        launchflow_uri = LaunchFlowURI(
            project_name=self.launchflow_yaml.project,
            environment_name=self.launchflow_yaml.default_environment,
            service_name="my-aws-service",
        )
        build_mock.assert_called_once_with(
            environment_state=self.dev_environment,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            build_log_file=mock.ANY,
            build_local=True,
        )
        release_mock.assert_called_once_with(
            release_inputs="ecr.io/project/service:latest",
            environment_state=self.dev_environment,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            release_log_file=mock.ANY,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.UNKNOWN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.deployment_id, deployment_id)
        self.assertEqual(
            got_service.service_url,
            "http://service-1234-alb.us-east-1.elb.amazonaws.com",
        )
        self.assertEqual(got_service.aws_arn, "service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)
        # Make sure the docker_image is no longer set
        self.assertEqual(got_service.docker_image, None)

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_aws_service_build_failure(
        self,
        time_mock,
        uuid_mock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id=None,
            aws_arn="service-1234",
        )
        # Simulate a failure during the build step
        build_mock = mock.AsyncMock(side_effect=exceptions.MissingAWSDependency())
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag off and verify the inputs / outputs
            service = AWSService("my-aws-service", build_directory=tmpdirname)

            service.build = build_mock
            service.release = release_mock
            service.inputs = mock.Mock(return_value=Inputs())
            service.outputs = mock.Mock(return_value=service_outputs)
            service.resources = mock.Mock(return_value=[])

            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=False,
            )
            self.assertFalse(result.success)

        # Ensure the release step is not called
        release_mock.assert_not_called()

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.UNKNOWN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.aws_arn, "service-1234")
        # NOTE: only deployment_id and service url are None since the create step was successful
        self.assertEqual(got_service.deployment_id, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.DEPLOY_FAILED)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_no_from_service(
        self,
        time_mock,
        uuid_mock,
    ):
        service = CloudRunService("my-gcp-service")
        result = await deploy_flows.promote(
            service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.plan_results), 0)
        self.assertEqual(len(result.failed_plans), 1)
        self.assertIn("does not exist", result.failed_plans[0].error_message)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_service_from_product_mismatch(
        self,
        time_mock,
        uuid_mock,
    ):
        # Tests the case where the new service definition in code / yaml doesnt match
        # the existing service in the source environment
        from_service = CloudRunService("my-service")
        to_service = ECSFargateService("my-service")

        from_service_manager = self.dev_environment_manager.create_service_manager(
            from_service.name
        )
        await from_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=from_service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs=from_service.inputs().to_dict(),
                deployment_id="1640995200000",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        result = await deploy_flows.promote(
            to_service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.plan_results), 0)
        self.assertEqual(len(result.failed_plans), 1)
        self.assertIn(
            "already exists with a different product",
            result.failed_plans[0].error_message,
        )

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_service_to_product_mismatch(
        self,
        time_mock,
        uuid_mock,
    ):
        # Tests the case where the new service definition doesnt match
        # what's currently deployed in the target environment
        from_service = CloudRunService("my-service")
        existing_to_service = CloudRunService("my-service")
        new_to_service = ECSFargateService("my-service")

        from_service_manager = self.dev_environment_manager.create_service_manager(
            from_service.name
        )
        await from_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=from_service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs=from_service.inputs().to_dict(),
                deployment_id="1640995200000",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        to_service_manager = self.prod_environment_manager.create_service_manager(
            existing_to_service.name
        )
        await to_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=existing_to_service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs=existing_to_service.inputs().to_dict(),
                deployment_id="1640995200000",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        result = await deploy_flows.promote(
            new_to_service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.plan_results), 0)
        self.assertEqual(len(result.failed_plans), 1)
        self.assertIn(
            "already exists with a different product",
            result.failed_plans[0].error_message,
        )

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_gcp_cloud_run_failure(
        self,
        time_mock,
        uuid_mock,
    ):
        # Simulate an exception being raised during the promote service flow
        promote_mock = mock.AsyncMock(side_effect=exceptions.MissingGCPDependency())

        # Create a dev service to promote to prod
        service = CloudRunService("my-gcp-service")
        service_outputs = ServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
        service.promote = promote_mock
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        await service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs=service.inputs().to_dict(),
                deployment_id="1640995200000",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        result = await deploy_flows.promote(
            service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.plan_results), 1)
        self.assertEqual(len(result.failed_plans), 0)
        self.assertIsInstance(
            result.plan_results[0], deploy_flows.PromoteFlowServiceResult
        )
        self.assertIn(
            "GCP dependencies are not installed",
            result.plan_results[0].promote_image_result.error_message,
        )

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.prod_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.GCP_CLOUD_RUN)
        self.assertEqual(got_service.inputs, None)
        self.assertEqual(got_service.deployment_id, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.gcp_id, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.PROMOTE_FAILED)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_gcp_cloud_run_successful(
        self,
        time_mock,
        uuid_mock,
    ):
        # Setup the promote service mock
        promote_mock = mock.AsyncMock(return_value="gcr.io/project/service:latest")
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        service = CloudRunService("my-gcp-service")

        service.promote = promote_mock
        service.release = release_mock
        service.inputs = mock.Mock(return_value=Inputs())
        service.outputs = mock.Mock(return_value=service_outputs)
        service.resources = mock.Mock(return_value=[])

        dev_service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        prod_service_manager = self.prod_environment_manager.create_service_manager(
            service.name
        )
        await dev_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs=service.inputs().to_dict(),
                deployment_id="from_deployment_id",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )
        await prod_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                gcp_id="prod-service-1234",
                status=enums.ServiceStatus.READY,
                inputs=None,
                deployment_id=None,
                service_url=None,
            ),
            lock_id="lock",
        )

        # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
        result = await deploy_flows.promote(
            service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertTrue(result.success)

        deployment_id = "1640995200000"

        from_service_state = await dev_service_manager.load_service()
        promote_mock.assert_called_once_with(
            from_environment_state=self.dev_environment,
            to_environment_state=self.prod_environment,
            from_launchflow_uri=LaunchFlowURI(
                project_name=self.launchflow_yaml.project,
                environment_name=self.dev_environment_manager.environment_name,
                service_name=service.name,
            ),
            to_launchflow_uri=LaunchFlowURI(
                project_name=self.launchflow_yaml.project,
                environment_name=self.prod_environment_manager.environment_name,
                service_name=service.name,
            ),
            from_deployment_id="from_deployment_id",
            to_deployment_id=deployment_id,
            promote_log_file=mock.ANY,
            promote_local=False,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await prod_service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.GCP_CLOUD_RUN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.deployment_id, deployment_id)
        self.assertEqual(got_service.service_url, "https://service-1234-uc.a.run.app")
        self.assertEqual(got_service.gcp_id, "prod-service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)
        # Make sure the docker_image is no longer set
        self.assertEqual(got_service.docker_image, None)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_aws_lambda_failure(
        self,
        time_mock,
        uuid_mock,
    ):
        # Simulate an exception being raised during the promote service flow
        promote_mock = mock.AsyncMock(side_effect=exceptions.MissingAWSDependency())

        # Create a dev service to promote to prod
        service = LambdaService("my-aws-service", handler="app.handler")
        service_outputs = ServiceOutputs(
            service_url="https://my-aws-service.us-west-2.amazonaws.com",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
        service.promote = promote_mock
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        await service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ServiceProduct.AWS_LAMBDA,
                inputs=service.inputs().to_dict(),
                deployment_id="1640995200000",
                service_url="https://my-aws-service.us-west-2.amazonaws.com",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        result = await deploy_flows.promote(
            service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.plan_results), 1)
        self.assertEqual(len(result.failed_plans), 0)
        self.assertIsInstance(
            result.plan_results[0], deploy_flows.PromoteFlowServiceResult
        )
        self.assertIn(
            "AWS dependencies are not installed",
            result.plan_results[0].promote_image_result.error_message,
        )

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.prod_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_LAMBDA)
        self.assertEqual(got_service.inputs, None)
        self.assertEqual(got_service.deployment_id, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.gcp_id, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.PROMOTE_FAILED)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_aws_lambda_successful(
        self,
        time_mock,
        uuid_mock,
    ):
        # Setup the promote service mock
        promote_mock = mock.AsyncMock(return_value="ecr.io/project/service:latest")
        release_mock = mock.AsyncMock(return_value=None)

        service_outputs = ServiceOutputs(
            service_url="https://my-aws-service.us-west-2.amazonaws.com",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"

        service = LambdaService("my-aws-service", handler="app.handler")

        service.promote = promote_mock
        service.release = release_mock
        service.inputs = mock.Mock(return_value=Inputs())
        service.outputs = mock.Mock(return_value=service_outputs)
        service.resources = mock.Mock(return_value=[])

        dev_service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        prod_service_manager = self.prod_environment_manager.create_service_manager(
            service.name
        )
        await dev_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ServiceProduct.AWS_LAMBDA,
                inputs=service.inputs().to_dict(),
                deployment_id="from_deployment_id",
                service_url="https://my-aws-service.us-west-2.amazonaws.com",
                aws_arn="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )
        await prod_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ServiceProduct.AWS_LAMBDA,
                aws_arn="prod-service-1234",
                status=enums.ServiceStatus.READY,
                inputs=None,
                deployment_id=None,
                service_url=None,
            ),
            lock_id="lock",
        )

        # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
        result = await deploy_flows.promote(
            service,
            from_environment=self.dev_environment_manager.environment_name,
            to_environment=self.prod_environment_manager.environment_name,
            prompt=False,
        )
        self.assertTrue(result.success)

        deployment_id = "1640995200000"

        from_service_state = await dev_service_manager.load_service()
        promote_mock.assert_called_once_with(
            from_environment_state=self.dev_environment,
            to_environment_state=self.prod_environment,
            from_launchflow_uri=LaunchFlowURI(
                project_name=self.launchflow_yaml.project,
                environment_name=self.dev_environment_manager.environment_name,
                service_name=service.name,
            ),
            to_launchflow_uri=LaunchFlowURI(
                project_name=self.launchflow_yaml.project,
                environment_name=self.prod_environment_manager.environment_name,
                service_name=service.name,
            ),
            from_deployment_id="from_deployment_id",
            to_deployment_id=deployment_id,
            promote_log_file=mock.ANY,
            promote_local=False,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await prod_service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_LAMBDA)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.deployment_id, deployment_id)
        self.assertEqual(
            got_service.service_url, "https://my-aws-service.us-west-2.amazonaws.com"
        )
        self.assertEqual(got_service.aws_arn, "prod-service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)
        # Make sure the docker_image is no longer set
        self.assertEqual(got_service.docker_image, None)

    async def test_force_unlock_service_success(self):
        service_manager = self.dev_environment_manager.create_service_manager(
            "test-service"
        )

        # Lock the service
        lock = await service_manager.lock_service(
            LockOperation(operation_type=OperationType.DEPLOY_SERVICE)
        )

        # Force unlock the service
        await service_manager.force_unlock_service()

        # Try to lock the service again to ensure it's unlocked
        lock = await service_manager.lock_service(
            LockOperation(operation_type=OperationType.DEPLOY_SERVICE)
        )
        await lock.release()

    async def test_force_unlock_service_not_locked(self):
        service_manager = self.dev_environment_manager.create_service_manager(
            "test-service"
        )

        with self.assertRaises(exceptions.LockNotFound):
            await service_manager.force_unlock_service()


if __name__ == "__main__":
    unittest.main()
