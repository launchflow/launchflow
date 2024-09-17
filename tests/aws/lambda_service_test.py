import json
import os
import unittest
from unittest import mock

import boto3
import pytest
from moto import mock_aws

from launchflow.aws.api_gateway import APIGateway, APIGatewayOutputs
from launchflow.aws.lambda_function import (
    LambdaFunctionOutputs,
    LambdaFunctionURLOutputs,
    LambdaRuntime,
)
from launchflow.aws.lambda_service import (
    APIGatewayURL,
    LambdaService,
    LambdaServiceReleaseInputs,
)
from launchflow.config import config
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import ServiceOutputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class LambdaServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dev_launchflow_uri = LaunchFlowURI(
            project_name="test-project",
            environment_name="dev-test-environment",
        )
        self.prod_launchflow_uri = LaunchFlowURI(
            project_name="test-project",
            environment_name="prod-test-environment",
        )
        self.dev_aws_environment_config = AWSEnvironmentConfig(
            account_id="test-account-id",
            region="us-west-2",
            iam_role_arn="arn:aws:iam::123456789012:role/test-role",
            vpc_id="vpc-123456",
            artifact_bucket="test-artifacts",
        )
        self.prod_aws_environment_config = AWSEnvironmentConfig(
            account_id="test-account-id",
            region="us-west-2",
            iam_role_arn="arn:aws:iam::123456789012:role/test-role",
            vpc_id="vpc-123456",
            artifact_bucket="test-artifacts",
        )
        self.launchflow_yaml_abspath = os.path.dirname(
            os.path.abspath(config.launchflow_yaml.config_path)
        )

    # NOTE: We only support local builds for Lambda functions
    @mock.patch("launchflow.aws.lambda_service._zip_source")
    async def test_build_lambda(self, build_zip_mock: mock.MagicMock):
        service_name = "my-lambda-service"
        # Setup the build mocks
        fake_zip_bytes = b"fake-zip-bytes"
        build_zip_mock.return_value = fake_zip_bytes

        lambda_service = LambdaService(service_name, handler="app.handler")

        # Setup the resource output mocks
        lambda_function_outputs = LambdaFunctionOutputs(
            function_name=service_name,
            alias_name=self.dev_launchflow_uri.environment_name,
        )
        lambda_service._lambda_function.outputs = mock.MagicMock(
            return_value=lambda_function_outputs
        )

        with mock_aws():
            # Let the LambdaService assume the role
            iam_client = boto3.client("iam")
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            iam_client.create_role(
                RoleName="test-role",
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Lambda to assume",
            )

            # Create a fake Lambda function so we can test the build
            lambda_client = boto3.client(
                "lambda", region_name=self.dev_aws_environment_config.region
            )
            # Create the Lambda function
            lambda_client.create_function(
                FunctionName=lambda_function_outputs.function_name,
                Runtime=LambdaRuntime.PYTHON3_11.value,
                Role=self.dev_aws_environment_config.iam_role_arn,  # type: ignore
                Handler="app.handler",
                Code={"ZipFile": fake_zip_bytes},
                Timeout=10,
                MemorySize=256,
            )

            # Run the build and validate the result / mock calls
            release_inputs = await lambda_service._build(
                aws_environment_config=self.dev_aws_environment_config,
                launchflow_uri=self.dev_launchflow_uri,
                deployment_id="test-deployment-id",
                build_log_file=mock.MagicMock(),
                build_local=False,  # NOTE: This argument is not used by LambdaService
            )
            # This should be the first version of the function since we just created it
            self.assertEqual(release_inputs.function_version, "1")

        build_zip_mock.assert_called_once_with(
            build_directory=self.launchflow_yaml_abspath,
            build_ignore=mock.ANY,
            python_version="3.11",
            requirements_txt_path=None,
        )

    @mock.patch("launchflow.aws.lambda_service.requests")
    async def test_promote_lambda(self, requests_mock: mock.MagicMock):
        service_name = "my-lambda-service"
        lambda_service = LambdaService(service_name, handler="app.handler")

        fake_from_zip_bytes = b"fake-from-zip-bytes"
        fake_to_zip_bytes = b"fake-to-zip-bytes"

        # NOTE: This mocks out the step that downloads the zip file from the artifact bucket
        mock_response = mock.MagicMock()
        mock_response.content = fake_from_zip_bytes
        requests_mock.get.return_value = mock_response

        # NOTE (to future self): We might need to change the output mocks if the
        # order that the outputs are called changes in the promote method
        # Setup the resource output mocks (the from.outputs() is called first)
        from_lambda_function_outputs = LambdaFunctionOutputs(
            function_name=f"from-{service_name}",
            alias_name=self.dev_launchflow_uri.environment_name,
        )
        to_lambda_function_outputs = LambdaFunctionOutputs(
            function_name=f"to-{service_name}",
            alias_name=self.prod_launchflow_uri.environment_name,
        )
        lambda_service._lambda_function.outputs = mock.MagicMock(
            side_effect=[from_lambda_function_outputs, to_lambda_function_outputs]
        )

        with mock_aws():
            # Let the LambdaService assume the role shared by the 2 functions
            iam_client = boto3.client("iam")
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            iam_client.create_role(
                RoleName="test-role",
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Lambda to assume",
            )

            # Create a fake Lambda function so we can test the build
            lambda_client = boto3.client(
                "lambda", region_name=self.dev_aws_environment_config.region
            )
            # Create the from Lambda function + alias
            from_func_info = lambda_client.create_function(
                FunctionName=from_lambda_function_outputs.function_name,
                Runtime=LambdaRuntime.PYTHON3_11.value,
                Role=self.dev_aws_environment_config.iam_role_arn,  # type: ignore
                Handler="app.handler",
                Code={"ZipFile": fake_from_zip_bytes},
                Timeout=10,
                MemorySize=256,
                Publish=True,
            )
            lambda_client.create_alias(
                FunctionName=from_lambda_function_outputs.function_name,
                Name=from_lambda_function_outputs.alias_name,
                FunctionVersion="1",
            )
            # Create the to Lambda function + alias
            to_func_info = lambda_client.create_function(
                FunctionName=to_lambda_function_outputs.function_name,
                Runtime=LambdaRuntime.PYTHON3_11.value,
                Role=self.prod_aws_environment_config.iam_role_arn,  # type: ignore
                Handler="app.handler",
                Code={"ZipFile": fake_to_zip_bytes},
                Timeout=10,
                MemorySize=256,
                Publish=True,
            )
            lambda_client.create_alias(
                FunctionName=to_lambda_function_outputs.function_name,
                Name=to_lambda_function_outputs.alias_name,
                FunctionVersion="1",
            )

            # Make sure the from and to functions CodeSha256 hashses are different
            self.assertNotEqual(
                from_func_info["CodeSha256"], to_func_info["CodeSha256"]
            )

            # Run the promote and validate the result / mock calls
            release_inputs = await lambda_service._promote(
                from_aws_environment_config=self.dev_aws_environment_config,
                to_aws_environment_config=self.prod_aws_environment_config,
                from_launchflow_uri=self.dev_launchflow_uri,
                to_launchflow_uri=self.prod_launchflow_uri,
                from_deployment_id="from-deployment-id",
                to_deployment_id="to-deployment-id",
                promote_log_file=mock.MagicMock(),
                promote_local=False,
            )

            # This should be the second version of the function since we just promoted it
            self.assertEqual(release_inputs.function_version, "2")

            # Ensure that the new function version now has the same CodeSha256 hash as the from function
            to_func_info = lambda_client.get_function(
                FunctionName=to_lambda_function_outputs.function_name,
                Qualifier=release_inputs.function_version,
            )
            self.assertEqual(
                to_func_info["Configuration"]["CodeSha256"],  # type: ignore
                from_func_info["CodeSha256"],
            )

    # # TODO: Test the failure case once the release logs are implemented
    async def test_release_lambda_successful(self):
        service_name = "my-lambda-service"

        lambda_service = LambdaService(service_name, handler="app.handler")

        # Setup the resource output mocks
        lambda_function_outputs = LambdaFunctionOutputs(
            function_name=service_name,
            alias_name=self.dev_launchflow_uri.environment_name,
        )
        lambda_service._lambda_function.outputs = mock.MagicMock(
            return_value=lambda_function_outputs
        )
        lambda_url_outputs = LambdaFunctionURLOutputs(
            function_url="https://test-url.execute-api.us-west-2.amazonaws.com/test",
            url_id="test",
        )
        lambda_service._lambda_function_url.outputs = mock.MagicMock(  # type: ignore
            return_value=lambda_url_outputs
        )

        with mock_aws():
            # Let the LambdaService assume the role
            iam_client = boto3.client("iam")
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            iam_client.create_role(
                RoleName="test-role",
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Lambda to assume",
            )

            # Create a fake Lambda function so we can test the build
            lambda_client = boto3.client(
                "lambda", region_name=self.dev_aws_environment_config.region
            )
            # Create the Lambda function + alias
            lambda_client.create_function(
                FunctionName=lambda_function_outputs.function_name,
                Runtime=LambdaRuntime.PYTHON3_11.value,
                Role=self.dev_aws_environment_config.iam_role_arn,  # type: ignore
                Handler="app.handler",
                Code={"ZipFile": b"fake-zip-bytes"},
                Timeout=10,
                MemorySize=256,
                Publish=True,
            )
            lambda_client.create_alias(
                FunctionName=lambda_function_outputs.function_name,
                Name=lambda_function_outputs.alias_name,
                FunctionVersion="1",
            )

            # Create a new version of the function
            lambda_client.update_function_code(
                FunctionName=lambda_function_outputs.function_name,
                ZipFile=b"updated-zip-bytes",
                Publish=True,
            )

            # Ensure that the function version is still 1 before the release
            function_version_before_release = lambda_client.get_function(
                FunctionName=lambda_function_outputs.function_name,
                Qualifier=lambda_function_outputs.alias_name,
            )["Configuration"][
                "Version"
            ]  # type: ignore
            self.assertEqual(function_version_before_release, "1")

            # Run the release and validate the result
            await lambda_service._release(
                release_inputs=LambdaServiceReleaseInputs(function_version="2"),
                aws_environment_config=self.dev_aws_environment_config,
                launchflow_uri=self.dev_launchflow_uri,
                deployment_id="test-deployment-id",
                release_log_file=mock.MagicMock(),
            )
            # This should match the URL from the outputs
            self.assertEqual(
                lambda_service.outputs().service_url, lambda_url_outputs.function_url
            )

            # Ensure that the function version is now 2 after the release
            function_version_after_release = lambda_client.get_function(
                FunctionName=lambda_function_outputs.function_name,
                Qualifier=lambda_function_outputs.alias_name,
            )["Configuration"][
                "Version"
            ]  # type: ignore
            self.assertEqual(function_version_after_release, "2")

    async def test_lambda_service_outputs(self):
        default_lambda_service = LambdaService(
            "my-lambda-service", handler="app.handler"
        )
        # Setup the resource output mocks for the default service
        lambda_function_outputs = LambdaFunctionOutputs(
            function_name="my-lambda-service",
            alias_name=self.dev_launchflow_uri.environment_name,
        )
        default_lambda_service._lambda_function.outputs = mock.MagicMock(
            return_value=lambda_function_outputs
        )
        lambda_function_url_outputs = LambdaFunctionURLOutputs(
            function_url="https://test-url.lambda-api.us-west-2.amazonaws.com",
            url_id="test",
        )
        default_lambda_service._lambda_function_url.outputs = mock.MagicMock(  # type: ignore
            return_value=lambda_function_url_outputs
        )

        api_gateway_lambda_service = LambdaService(
            "my-lambda-service",
            handler="app.handler",
            url=APIGatewayURL(api_gateway=APIGateway("my-api-gateway"), path="/test"),
        )
        # Setup the resource output mocks for the API Gateway service
        api_gateway_lambda_service._lambda_function.outputs = mock.MagicMock(
            return_value=lambda_function_outputs
        )
        api_gateway_outputs = APIGatewayOutputs(
            api_gateway_id="test-api-id",
            api_gateway_endpoint="https://test-api-url.execute-api.us-west-2.amazonaws.com",
        )
        api_gateway_lambda_service.url.api_gateway.outputs = mock.MagicMock(  # type: ignore
            return_value=api_gateway_outputs
        )

        # Fetch the outputs and assert that they are correct
        default_lambda_outputs = default_lambda_service.outputs()
        self.assertEqual(
            default_lambda_outputs,
            ServiceOutputs(
                service_url=lambda_function_url_outputs.function_url,
                dns_outputs=None,
            ),
        )

        api_gateway_lambda_outputs = api_gateway_lambda_service.outputs()
        self.assertEqual(
            api_gateway_lambda_outputs,
            ServiceOutputs(
                service_url=f"{api_gateway_outputs.api_gateway_endpoint}/test",
                dns_outputs=None,
            ),
        )
