import os
import unittest
from unittest import mock

import boto3
import pytest
from moto import mock_aws

from launchflow.aws.alb import ApplicationLoadBalancerOutputs
from launchflow.aws.codebuild_project import CodeBuildProjectOutputs
from launchflow.aws.ecr_repository import ECRRepositoryOutputs
from launchflow.aws.ecs_cluster import ECSClusterOutputs
from launchflow.aws.ecs_fargate import ECSFargateService, ECSFargateServiceReleaseInputs
from launchflow.aws.ecs_fargate_container import ECSFargateServiceContainerOutputs
from launchflow.config import config
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class ECSFargateServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.launchflow_uri = LaunchFlowURI(
            project_name="test-project",
            environment_name="test-environment",
        )
        self.aws_environment_config = AWSEnvironmentConfig(
            account_id="test-account-id",
            region="us-west-2",
            iam_role_arn="arn:aws:iam::123456789012:role/service-role/role-name",
            vpc_id="vpc-123456",
            artifact_bucket="test-artifacts",
        )
        self.deployment_id = "test-deployment-id"
        self.launchflow_yaml_abspath = os.path.dirname(
            os.path.abspath(config.launchflow_yaml.config_path)
        )

    @mock.patch("launchflow.aws.ecs_fargate.ECRDockerBuilder")
    async def test_build_ecs_fargate_docker_remote(
        self, build_docker_mock: mock.MagicMock
    ):
        service_name = "my-ecs-service"
        # Setup the build mocks
        builder_mock = mock.AsyncMock()
        build_docker_mock.return_value = builder_mock
        fake_docker_image = (
            f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}:latest"
        )
        builder_mock.build_with_docker_remote.return_value = fake_docker_image

        ecs_fargate_service = ECSFargateService(service_name, dockerfile="Dockerfile")
        # Setup the resource output mocks
        ecr_outputs = ECRRepositoryOutputs(
            repository_url=f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}"
        )
        ecs_fargate_service._ecr.outputs = mock.MagicMock(return_value=ecr_outputs)
        code_build_outputs = CodeBuildProjectOutputs(
            project_name="test-code-build-project"
        )
        ecs_fargate_service._code_build_project.outputs = mock.MagicMock(
            return_value=code_build_outputs
        )

        # Run the build and validate the result / mock calls
        release_inputs = await ecs_fargate_service._build(
            aws_environment_config=self.aws_environment_config,
            launchflow_uri=self.launchflow_uri,
            deployment_id=self.deployment_id,
            build_log_file=mock.MagicMock(),
            build_local=False,
        )
        self.assertEqual(release_inputs.docker_image, fake_docker_image)

        builder_mock.build_with_docker_remote.assert_called_once_with(
            "Dockerfile", "test-code-build-project"
        )

    @mock.patch("launchflow.aws.ecs_fargate.ECRDockerBuilder")
    async def test_build_ecs_fargate_nixpacks_remote(
        self, build_docker_mock: mock.MagicMock
    ):
        service_name = "my-ecs-service"
        # Setup the build mocks
        builder_mock = mock.AsyncMock()
        build_docker_mock.return_value = builder_mock
        fake_docker_image = (
            f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}:latest"
        )
        builder_mock.build_with_nixpacks_remote.return_value = fake_docker_image

        ecs_fargate_service = ECSFargateService(service_name)
        # Setup the resource output mocks
        ecr_outputs = ECRRepositoryOutputs(
            repository_url=f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}"
        )
        ecs_fargate_service._ecr.outputs = mock.MagicMock(return_value=ecr_outputs)
        code_build_outputs = CodeBuildProjectOutputs(
            project_name="test-code-build-project"
        )
        ecs_fargate_service._code_build_project.outputs = mock.MagicMock(
            return_value=code_build_outputs
        )

        # Run the build and validate the result / mock calls
        release_inputs = await ecs_fargate_service._build(
            aws_environment_config=self.aws_environment_config,
            launchflow_uri=self.launchflow_uri,
            deployment_id=self.deployment_id,
            build_log_file=mock.MagicMock(),
            build_local=False,
        )
        self.assertEqual(release_inputs.docker_image, fake_docker_image)

        builder_mock.build_with_nixpacks_remote.assert_called_once_with(
            "test-code-build-project"
        )

    @mock.patch("launchflow.aws.ecs_fargate.ECRDockerBuilder")
    async def test_build_ecs_fargate_docker_local(
        self, build_docker_mock: mock.MagicMock
    ):
        service_name = "my-ecs-service"
        # Setup the build mocks
        builder_mock = mock.AsyncMock()
        build_docker_mock.return_value = builder_mock
        fake_docker_image = (
            f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}:latest"
        )
        builder_mock.build_with_docker_local.return_value = fake_docker_image

        ecs_fargate_service = ECSFargateService(service_name, dockerfile="Dockerfile")
        # Setup the resource output mocks
        ecr_outputs = ECRRepositoryOutputs(
            repository_url=f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}"
        )
        ecs_fargate_service._ecr.outputs = mock.MagicMock(return_value=ecr_outputs)

        # Run the build and validate the result / mock calls
        release_inputs = await ecs_fargate_service._build(
            aws_environment_config=self.aws_environment_config,
            launchflow_uri=self.launchflow_uri,
            deployment_id=self.deployment_id,
            build_log_file=mock.MagicMock(),
            build_local=True,
        )
        self.assertEqual(release_inputs.docker_image, fake_docker_image)

        builder_mock.build_with_docker_local.assert_called_once_with("Dockerfile")

    @mock.patch("launchflow.aws.ecs_fargate.ECRDockerBuilder")
    async def test_build_ecs_fargate_nixpack_local(
        self, build_docker_mock: mock.MagicMock
    ):
        service_name = "my-ecs-service"
        # Setup the build mocks
        builder_mock = mock.AsyncMock()
        build_docker_mock.return_value = builder_mock
        fake_docker_image = (
            f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}:latest"
        )
        builder_mock.build_with_nixpacks_local.return_value = fake_docker_image

        ecs_fargate_service = ECSFargateService(service_name)
        # Setup the resource output mocks
        ecr_outputs = ECRRepositoryOutputs(
            repository_url=f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{service_name}"
        )
        ecs_fargate_service._ecr.outputs = mock.MagicMock(return_value=ecr_outputs)

        # Run the build and validate the result / mock calls
        release_inputs = await ecs_fargate_service._build(
            aws_environment_config=self.aws_environment_config,
            launchflow_uri=self.launchflow_uri,
            deployment_id=self.deployment_id,
            build_log_file=mock.MagicMock(),
            build_local=True,
        )
        self.assertEqual(release_inputs.docker_image, fake_docker_image)

        builder_mock.build_with_nixpacks_local.assert_called_once_with()

    # TODO: Test the promote flow once its implemented
    async def test_promote_ecs_fargate(self):
        ecs_fargate_service = ECSFargateService("my-ecs-service")

        with self.assertRaises(NotImplementedError):
            await ecs_fargate_service._promote(
                from_aws_environment_config=self.aws_environment_config,
                to_aws_environment_config=self.aws_environment_config,
                from_launchflow_uri=self.launchflow_uri,
                to_launchflow_uri=self.launchflow_uri,
                from_deployment_id=self.deployment_id,
                to_deployment_id=self.deployment_id,
                promote_log_file=mock.MagicMock(),
                promote_local=False,
            )

    # TODO: Test the failure case once the release logs are implemented
    async def test_release_ecs_fargate_successful(self):
        service_name = "my-ecs-service"
        ecs_fargate_service = ECSFargateService(
            service_name, cpu=512, memory=1024, port=80
        )

        # Setup the resource output mocks
        ecs_cluster_outputs = ECSClusterOutputs(
            cluster_name="test-cluster",
        )
        ecs_fargate_service._ecs_cluster.outputs = mock.MagicMock(
            return_value=ecs_cluster_outputs
        )
        alb_outputs = ApplicationLoadBalancerOutputs(
            alb_dns_name="test-alb-1234567890.us-west-2.elb.amazonaws.com",
            alb_security_group_id="sg-123456",
            alb_target_group_arn="arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-target-group/123456",
        )
        ecs_fargate_service._alb.outputs = mock.MagicMock(return_value=alb_outputs)
        ecs_fargate_service_container_outputs = ECSFargateServiceContainerOutputs(
            public_ip="1.3.3.7"
        )
        ecs_fargate_service._ecs_fargate_service_container.outputs = mock.MagicMock(
            return_value=ecs_fargate_service_container_outputs
        )

        with mock_aws():
            # Setup the mock ECS data
            ecs_client = boto3.client(
                "ecs", region_name=self.aws_environment_config.region
            )
            # Create the ECS Cluster
            ecs_client.create_cluster(clusterName=ecs_cluster_outputs.cluster_name)
            ecs_service_name = (
                ecs_fargate_service._ecs_fargate_service_container.resource_id
            )
            # Create the ECS task definition that will be updated
            task_definition_name = f"{ecs_service_name}-task"
            ecs_client.register_task_definition(
                family=task_definition_name,
                containerDefinitions=[
                    {
                        "name": ecs_service_name,
                        "image": "old-image",  # This should be updated by the release
                        "cpu": 256,  # This should be updated by the release
                        "memory": 512,  # This should be updated by the release
                        "portMappings": [
                            {
                                "containerPort": 1337,  # This should be updated by the release
                                "hostPort": 1337,  # This should be updated by the release
                            }
                        ],
                    }
                ],
            )
            # Create the ECS Service
            ecs_client.create_service(
                cluster=ecs_cluster_outputs.cluster_name,
                serviceName=ecs_service_name,
                taskDefinition=f"{ecs_service_name}-task",
                desiredCount=1,
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": ["subnet-123456"],
                        "securityGroups": [alb_outputs.alb_security_group_id],
                        "assignPublicIp": "ENABLED",
                    }
                },
            )

            # Mock out the client imported in the method so we can override the waiter
            with mock.patch("boto3.client") as ecs_client_mock:
                ecs_client_mock.return_value = ecs_client
                # Mock out the waiter
                ecs_client.get_waiter = mock.MagicMock()

                # Run the release
                await ecs_fargate_service._release(
                    release_inputs=ECSFargateServiceReleaseInputs(
                        docker_image="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-ecs-service:latest"
                    ),
                    aws_environment_config=self.aws_environment_config,
                    launchflow_uri=self.launchflow_uri,
                    deployment_id=self.deployment_id,
                    release_log_file=mock.MagicMock(),
                )

            # Validate the result / updated ECS service state
            self.assertEqual(
                ecs_fargate_service.outputs().service_url,
                f"http://{alb_outputs.alb_dns_name}",
            )

            # Validate the ECS service was updated with the new image, cpu, memory, and port mappings
            task_definition = ecs_client.describe_task_definition(
                taskDefinition=f"{task_definition_name}:2"
            )["taskDefinition"]
            self.assertEqual(task_definition["cpu"], "512")
            self.assertEqual(task_definition["memory"], "1024")
            container_definition = task_definition["containerDefinitions"][0]
            self.assertEqual(
                container_definition["image"],
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-ecs-service:latest",
            )

            self.assertEqual(
                container_definition["portMappings"],
                [
                    {
                        "containerPort": 80,
                        "hostPort": 80,
                    }
                ],
            )
