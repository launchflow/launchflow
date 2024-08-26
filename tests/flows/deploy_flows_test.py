import datetime
import tempfile
import unittest
from unittest import mock

import pytest

from launchflow import exceptions
from launchflow.aws.ecs_fargate import ECSFargate
from launchflow.flows import deploy_flows
from launchflow.gcp.cloud_run import CloudRun
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models import enums, flow_state
from launchflow.service import DockerServiceOutputs
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

    async def test_deploy_gcp_service_no_environment(self):
        service = CloudRun("my-gcp-service")
        with pytest.raises(exceptions.EnvironmentNotFound):
            await deploy_flows.deploy(
                service, environment="does-not-exist", prompt=False
            )

    async def test_deploy_aws_service_no_environment(self):
        service = ECSFargate("my-aws-service")
        with pytest.raises(exceptions.EnvironmentNotFound):
            await deploy_flows.deploy(
                service, environment="does-not-exist", prompt=False
            )

    async def test_deploy_gcp_service_no_gcp_config(self):
        service = CloudRun("my-gcp-service")
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
        service = ECSFargate("my-aws-service")
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
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_gcp_service")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_cloud_run")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_cloud_run_successful(
        self,
        time_mock,
        uuid_mock,
        mock_release_gcp_service: mock.MagicMock,
        mock_build_gcp_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        # Setup the deploy service mock
        mock_build_gcp_service.return_value = (
            "gcr.io/project/service:latest",
            "build-logs",
        )
        mock_release_gcp_service.return_value = "https://service-1234-uc.a.run.app"

        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            service = CloudRun("my-gcp-service", build_directory=tmpdirname)
            service.outputs = mock.Mock(return_value=service_outputs)
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
        mock_build_gcp_service.assert_called_once_with(
            service,
            service_manager,
            self.dev_environment.gcp_config,
            deployment_id,
            True,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.GCP_CLOUD_RUN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.docker_image, "gcr.io/project/service:latest")
        self.assertEqual(got_service.service_url, "https://service-1234-uc.a.run.app")
        self.assertEqual(got_service.gcp_id, "service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_gcp_service")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_cloud_run")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_cloud_run_skip_build_no_service(
        self,
        time_mock,
        uuid_mock,
        mock_release_gcp_service: mock.MagicMock,
        mock_build_gcp_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        mock_release_gcp_service.return_value = "https://service-1234-uc.a.run.app"

        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            service = CloudRun("my-gcp-service", build_directory=tmpdirname)
            service.outputs = mock.Mock(return_value=service_outputs)
            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                skip_build=True,
            )
            self.assertTrue(result.success)

        # These are not called because the deploy failed to plan
        mock_build_gcp_service.assert_not_called()
        mock_release_gcp_service.assert_not_called()

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_gcp_service")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_cloud_run")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_cloud_run_skip_build_success(
        self,
        time_mock,
        uuid_mock,
        mock_release_gcp_service: mock.MagicMock,
        mock_build_gcp_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        mock_release_gcp_service.return_value = "https://service-1234-uc.a.run.app"

        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"
        service_name = "my-gcp-service"
        dev_service_manager = self.dev_environment_manager.create_service_manager(
            service_name
        )

        await dev_service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service_name,
                cloud_provider=enums.CloudProvider.GCP,
                product=enums.ServiceProduct.GCP_CLOUD_RUN,
                inputs={},
                docker_image="gcr.io/project/service:latest",
                service_url="https://service-1234-uc.a.run.app",
                gcp_id="service-1234",
                status=enums.ServiceStatus.READY,
            ),
            lock_id="lock",
        )

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            service = CloudRun("my-gcp-service", build_directory=tmpdirname)
            service.outputs = mock.Mock(return_value=service_outputs)
            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                skip_build=True,
            )
            self.assertTrue(result.success)
            mock_release_gcp_service.assert_called_with(
                docker_image="gcr.io/project/service:latest",
                service_manager=mock.ANY,
                gcp_environment_config=self.dev_environment.gcp_config,
                cloud_run_service=service,
                deployment_id="1640995200000",
            )

        # These are not called because the deploy failed to plan
        mock_build_gcp_service.assert_not_called()

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_aws_service")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_ecs_fargate")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_aws_ecs_fargate_successful(
        self,
        time_mock,
        uuid_mock,
        mock_release_aws_service: mock.MagicMock,
        mock_build_aws_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id=None,
            aws_arn="service-1234",
        )
        # Setup the deploy service mock
        mock_build_aws_service.return_value = (
            "ecr.io/project/service:latest",
            "build-logs",
        )
        mock_release_aws_service.return_value = (
            "http://service-1234-alb.us-east-1.elb.amazonaws.com"
        )

        service_outputs = DockerServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            docker_repository="ecr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag on and verify the inputs / outputs
            service = ECSFargate("my-aws-service", build_directory=tmpdirname)
            service.outputs = mock.Mock(return_value=service_outputs)
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
        mock_build_aws_service.assert_called_once_with(
            service,
            service_manager,
            self.dev_environment.aws_config,
            deployment_id,
            True,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_ECS_FARGATE)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.docker_image, "ecr.io/project/service:latest")
        self.assertEqual(
            got_service.service_url,
            "http://service-1234-alb.us-east-1.elb.amazonaws.com",
        )
        self.assertEqual(got_service.aws_arn, "service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)

    # TODO: Add a test that mocks out steps in the workflow, to handle branching logic between deploy and promote
    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_gcp_service")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_gcp_cloud_run_failure(
        self,
        time_mock,
        uuid_mock,
        mock_build_gcp_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id="service-1234",
            aws_arn=None,
        )
        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"

        # Simulate an exception being raised during the deploy service flow
        mock_build_gcp_service.side_effect = exceptions.MissingGCPDependency()

        # Call the deploy service flow with the build_local flag off and verify the inputs / outputs
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            service = CloudRun(
                "my-gcp-service", build_directory=tmpdirname, dockerfile="Dockerfile"
            )
            service.outputs = mock.Mock(return_value=service_outputs)
            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=False,
            )
            self.assertFalse(result.success)

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.GCP_CLOUD_RUN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.gcp_id, "service-1234")
        # NOTE: only docker image and service url are None since the create step was successful
        self.assertEqual(got_service.docker_image, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.DEPLOY_FAILED)

    @mock.patch("launchflow.flows.create_flows.create_tofu_resource")
    @mock.patch("launchflow.flows.deploy_flows.build_and_push_aws_service")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_deploy_aws_ecs_fargate_failure(
        self,
        time_mock,
        uuid_mock,
        mock_build_aws_service: mock.MagicMock,
        mock_create_tofu_resource: mock.MagicMock,
    ):
        # Setup the create service mock
        mock_create_tofu_resource.return_value = ApplyResourceTofuOutputs(
            gcp_id=None,
            aws_arn="service-1234",
        )
        service_outputs = DockerServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            docker_repository="ecr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"
        # Simulate an exception being raised during the deploy service flow
        mock_build_aws_service.side_effect = exceptions.MissingAWSDependency()

        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(f"{tmpdirname}/Dockerfile", "w") as f:
                f.write("FROM python:3.11\n")
            # Call the deploy service flow with the build_local flag off and verify the inputs / outputs
            service = ECSFargate(
                "my-aws-service",
                build_directory=tmpdirname,
                dockerfile="Dockerfile",
            )
            service.outputs = mock.Mock(return_value=service_outputs)
            result = await deploy_flows.deploy(
                service,
                environment=self.dev_environment_manager.environment_name,
                prompt=False,
                build_local=False,
            )
            self.assertFalse(result.success)

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_ECS_FARGATE)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.aws_arn, "service-1234")
        # NOTE: only docker image and service url are None since the create step was successful
        self.assertEqual(got_service.docker_image, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.DEPLOY_FAILED)

    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_no_from_service(
        self,
        time_mock,
        uuid_mock,
    ):
        service = CloudRun("my-gcp-service")
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
        from_service = CloudRun("my-service")
        to_service = ECSFargate("my-service")

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
                docker_image="gcr.io/project/service:latest",
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
        from_service = CloudRun("my-service")
        existing_to_service = CloudRun("my-service")
        new_to_service = ECSFargate("my-service")

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
                docker_image="gcr.io/project/service:latest",
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
                docker_image="gcr.io/project/service:latest",
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

    @mock.patch("launchflow.flows.deploy_flows.promote_gcp_service_image")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_gcp_cloud_run_failure(
        self,
        time_mock,
        uuid_mock,
        mock_promote_gcp_service: mock.MagicMock,
    ):
        # Simulate an exception being raised during the promote service flow
        mock_promote_gcp_service.side_effect = exceptions.MissingGCPDependency()

        # Create a dev service to promote to prod
        service = CloudRun("my-gcp-service")
        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
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
                docker_image="gcr.io/project/service:latest",
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
        self.assertIsInstance(result.plan_results[0], deploy_flows.PromoteServiceResult)
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
        self.assertEqual(got_service.docker_image, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.gcp_id, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.PROMOTE_FAILED)

    @mock.patch("launchflow.flows.deploy_flows.promote_gcp_service_image")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_cloud_run")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_gcp_cloud_run_successful(
        self,
        time_mock,
        uuid_mock,
        mock_release_docker_image: mock.MagicMock,
        mock_promote_gcp_service: mock.MagicMock,
    ):
        # Setup the promote service mock
        mock_promote_gcp_service.return_value = (
            "gcr.io/project/service:promoted",
            "promote-logs",
        )
        # Setup the release docker image mock
        mock_release_docker_image.return_value = (
            "https://prod-service-1234-uc.a.run.app"
        )

        # Create a dev service to promote to prod
        service = CloudRun("my-gcp-service")
        service_outputs = DockerServiceOutputs(
            service_url="https://service-1234-uc.a.run.app",
            docker_repository="gcr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.gcp_id = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
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
                docker_image="gcr.io/project/service:latest",
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
                docker_image=None,
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
        mock_promote_gcp_service.assert_called_once_with(
            service,
            from_service_state=from_service_state,
            from_gcp_environment_config=self.dev_environment.gcp_config,
            to_gcp_environment_config=self.prod_environment.gcp_config,
            deployment_id=deployment_id,
            promote_local=False,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await prod_service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.GCP_CLOUD_RUN)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.docker_image, "gcr.io/project/service:promoted")
        self.assertEqual(
            got_service.service_url, "https://prod-service-1234-uc.a.run.app"
        )
        self.assertEqual(got_service.gcp_id, "prod-service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)

    @mock.patch("launchflow.flows.deploy_flows.promote_aws_service_image")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_aws_ecs_fargate_failure(
        self,
        time_mock,
        uuid_mock,
        mock_promote_aws_service: mock.MagicMock,
    ):
        # Setup the promote service mock
        mock_promote_aws_service.side_effect = exceptions.MissingAWSDependency()

        # Create a dev service to promote to prod
        service = ECSFargate("my-aws-service")
        service_outputs = DockerServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            docker_repository="ecr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
        service_manager = self.dev_environment_manager.create_service_manager(
            service.name
        )
        await service_manager.save_service(
            service=flow_state.ServiceState(
                created_at=datetime.datetime(2021, 1, 1),
                updated_at=datetime.datetime(2021, 1, 1),
                name=service.name,
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ServiceProduct.AWS_ECS_FARGATE,
                inputs=service.inputs().to_dict(),
                docker_image="ecr.io/project/service:latest",
                service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
                aws_arn="service-1234",
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
        self.assertIsInstance(result.plan_results[0], deploy_flows.PromoteServiceResult)
        self.assertIn(
            "AWS dependencies are not installed",
            result.plan_results[0].promote_image_result.error_message,
        )

        # Ensure the correct service info was saved in the flow.state after failure
        service_manager = self.prod_environment_manager.create_service_manager(
            service.name
        )
        got_service = await service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_ECS_FARGATE)
        self.assertEqual(got_service.inputs, None)
        self.assertEqual(got_service.docker_image, None)
        self.assertEqual(got_service.service_url, None)
        self.assertEqual(got_service.gcp_id, None)
        self.assertEqual(got_service.status, enums.ServiceStatus.PROMOTE_FAILED)

    @mock.patch("launchflow.flows.deploy_flows.promote_aws_service_image")
    @mock.patch("launchflow.flows.deploy_flows.release_docker_image_to_ecs_fargate")
    @mock.patch("uuid.uuid4", return_value="lock")
    @mock.patch("time.time", return_value=1640995200.0)
    async def test_promote_aws_ecs_fargate_successful(
        self,
        time_mock,
        uuid_mock,
        mock_release_docker_image: mock.MagicMock,
        mock_promote_aws_service: mock.MagicMock,
    ):
        # Setup the release docker image mock
        mock_release_docker_image.return_value = (
            "http://service-1234-alb.us-east-1.elb.amazonaws.com"
        )
        # Setup the promote service mock
        mock_promote_aws_service.return_value = (
            "ecr.io/project/service:promoted",
            "promote-logs",
        )

        # Create a dev service to promote to prod
        service = ECSFargate("my-aws-service")
        service_outputs = DockerServiceOutputs(
            service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
            docker_repository="ecr.io/project/service",
            dns_outputs=None,
        )
        service_outputs.aws_arn = "service-1234"
        service.outputs = mock.Mock(return_value=service_outputs)
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
                product=enums.ServiceProduct.AWS_ECS_FARGATE,
                inputs=service.inputs().to_dict(),
                docker_image="ecr.io/project/service:latest",
                service_url="http://service-1234-alb.us-east-1.elb.amazonaws.com",
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
                status=enums.ServiceStatus.READY,
                cloud_provider=enums.CloudProvider.AWS,
                product=enums.ServiceProduct.AWS_ECS_FARGATE,
                inputs=None,
                docker_image=None,
                service_url=None,
                aws_arn="prod-service-1234",
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

        mock_promote_aws_service.assert_called_once_with(
            service,
            from_service_state=from_service_state,
            from_aws_environment_config=self.dev_environment.aws_config,
            to_aws_environment_config=self.prod_environment.aws_config,
            deployment_id=deployment_id,
            promote_local=False,
        )

        # Ensure the correct service info was saved in the flow.state
        got_service = await prod_service_manager.load_service()
        self.assertEqual(got_service.product, enums.ServiceProduct.AWS_ECS_FARGATE)
        self.assertEqual(got_service.inputs, service.inputs().to_dict())
        self.assertEqual(got_service.docker_image, "ecr.io/project/service:promoted")
        self.assertEqual(
            got_service.service_url,
            "http://service-1234-alb.us-east-1.elb.amazonaws.com",
        )
        self.assertEqual(got_service.aws_arn, "prod-service-1234")
        self.assertEqual(got_service.status, enums.ServiceStatus.READY)

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
