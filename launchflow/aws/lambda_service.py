import inspect
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import IO, Any, Dict, List, Optional, Union

import requests
from typing_extensions import Callable

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.api_gateway import (
    CORS,
    APIGateway,
    APIGatewayLambdaIntegration,
    APIGatewayRoute,
)
from launchflow.aws.lambda_function import (
    LambdaFunction,
    LambdaFunctionURL,
    LambdaRuntime,
)
from launchflow.aws.service import AWSService
from launchflow.config import config
from launchflow.models.enums import ServiceProduct
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import ServiceOutputs
from launchflow.workflows.utils import zip_source


def _get_relative_handler_import_path(func: Callable) -> str:
    # Get the absolute path of the directory containing the launchflow.yaml file
    launchflow_yaml_abspath = os.path.dirname(
        os.path.abspath(config.launchflow_yaml.config_path)
    )
    func_file_path = os.path.abspath(inspect.getfile(func))
    # Ensure the cwd has a trailing slash to avoid issues with relative path calculation
    cwd = os.path.abspath(launchflow_yaml_abspath) + os.path.sep
    # Convert the absolute path to a relative path with respect to the current working directory
    relative_path = os.path.relpath(func_file_path, cwd)
    # Convert the relative file path to a Python module path
    module_path = relative_path.replace(os.path.sep, ".").rsplit(".py", 1)[0]
    # Append the function name to the module path
    full_import_path = f"{module_path}.{func.__name__}"

    return full_import_path


def _zip_source(
    build_directory: str,
    build_ignore: List[str],
    python_version: Union[str, None],
    requirements_txt_path: Optional[str],
):
    # 1. create a temp dir
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copytree(build_directory, temp_dir, dirs_exist_ok=True, symlinks=True)

        # 2. Install packages from requirements.txt (if specified)
        if requirements_txt_path is not None and python_version is not None:
            # TODO: Update this to use uv for faster builds
            subprocess.check_call(
                f"pip install --no-cache-dir --platform manylinux2014_x86_64 --target={temp_dir} --implementation cp --python-version {python_version} --only-binary=:all: -r {requirements_txt_path}".split(),
                cwd=config.launchflow_yaml.project_directory_abs_path,
                stdout=subprocess.DEVNULL,  # TODO: Dump to the build logs file
                stderr=subprocess.DEVNULL,  # TODO: Dump to the build logs file
            )
            # Include __pycache__ directories and .pyc files in the build ignore to filter out artifacts that were created by the pip install
            build_ignore = list(set(build_ignore + ["__pycache__", "*.pyc"]))

        # 3. Zip the contents of the temp directory
        zip_file_path = os.path.join(temp_dir, "lambda.zip")
        zip_source(temp_dir, ignore_patterns=build_ignore, file=zip_file_path)

        # Read the zip file
        with open(zip_file_path, "rb") as zip_file:
            zip_file_content = zip_file.read()

    return zip_file_content


@dataclass
class LambdaServiceInputs(Inputs):
    pass


@dataclass
class PythonRuntime:
    """
    Python runtime options for Lambda functions.

    **Args:**
    - `runtime (LambdaRuntime)`: The Python runtime to use. Defaults to Python 3.11.
    - `requirements_txt_path (Optional[str])`: The path to the requirements.txt file to install dependencies from. Defaults to None.
    """

    runtime: LambdaRuntime = LambdaRuntime.PYTHON3_11
    requirements_txt_path: Optional[str] = None


# TODO: Add docstring for DockerRuntime once it's supported
@dataclass
class DockerRuntime:
    runtime: None = None
    dockerfile: str = "Dockerfile"


@dataclass
class LambdaURL:
    """
    URL configuration for a Lambda function.

    **Args:**
    - `public (bool)`: Whether the Lambda function is public. Defaults to True.
    - `cors (Optional[CORS])`: Optional CORS configuration for the Lambda function. Defaults to None.
    """

    public: bool = True
    cors: Optional[CORS] = None


@dataclass
class APIGatewayURL:
    """
    URL configuration for a Lambda function hosted on API Gateway.

    **Args:**
    - `api_gateway (APIGateway)`: The API Gateway resource to use.
    - `path (str)`: The path for the API Gateway route. Defaults to "/".
    - `request (str)`: The request method for the API Gateway route. Defaults to "GET".
    - `public (bool)`: Whether the API Gateway route is public. Defaults to True.
    """

    api_gateway: APIGateway
    path: str = "/"
    request = "GET"
    public: bool = True

    @property
    def route_key(self) -> str:
        if self.path == "/":
            return "$default"
        return f"{self.request} {self.path}"


@dataclass
class LambdaServiceReleaseInputs:
    function_version: str


class LambdaService(AWSService[LambdaServiceReleaseInputs]):
    """A service hosted on AWS Lambda.

    Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information, see [the official documentation](https://aws.amazon.com/lambda/).

    ### Example Usage

    #### Basic Usage

    ```python
    import launchflow as lf

    # This points to the `handler` function in the `app` module
    api = lf.aws.LambdaService("my-api", handler="app.handler")
    ```

    #### Custom Timeout and Memory Size

    ```python
    import launchflow as lf

    service = lf.aws.LambdaService(
        "my-lambda-service",
        handler="app.handler",
        timeout_seconds=30,
        memory_size_mb=512
    )
    ```

    #### Environment Variables

    ```python
    import launchflow as lf

    service = lf.aws.LambdaService(
        "my-lambda-service",
        handler="app.handler",
        env={"STAGE": "prod", "LOG_LEVEL": "debug"}
    )
    ```

    #### Custom URL Configuration

    ```python
    import launchflow as lf

    api_gateway = lf.aws.APIGateway("my-api-gateway")
    # The functions will share the same API Gateway
    read_api = lf.aws.LambdaService(
        "my-read-api",
        handler="app.list_users",
        url=lf.aws.APIGatewayURL(api_gateway=api_gateway, route_key="GET /users")
    )
    write_api = lf.aws.LambdaService(
        "my-write-api",
        handler="app.create_user",
        url=lf.aws.APIGatewayURL(api_gateway=api_gateway, route_key="POST /users")
    )
    ```
    """

    product = ServiceProduct.AWS_LAMBDA.value

    def __init__(
        self,
        name: str,
        *,
        handler: Union[str, Callable],
        timeout_seconds: int = 10,
        memory_size_mb: int = 256,
        env: Optional[Dict[str, str]] = None,
        url: Union[LambdaURL, APIGatewayURL] = LambdaURL(),
        runtime: Union[LambdaRuntime, PythonRuntime, DockerRuntime] = PythonRuntime(),
        domain: Optional[str] = None,  # TODO: Support custom domains for Lambda
        build_directory: str = ".",
        build_ignore: List[str] = [],  # type: ignore
    ) -> None:
        """Create a new Lambda Service.

        **Args:**
        - `name (str)`: The name of the service.
        - `handler (Union[str, Callable])`: The entry point for the Lambda function. If a callable is passed, it is converted to the proper handler string.
        - `timeout_seconds (int)`: The timeout in seconds for the Lambda function. Defaults to 10 seconds.
        - `memory_size_mb (int)`: The memory size for the Lambda function in MB. Defaults to 256 MB.
        - `env (Optional[Dict[str, str]])`: Optional environment variables for the Lambda function.
        - `url (Union[LambdaURL, APIGatewayURL])`: Optional URL configuration, defaults to a public Lambda URL.
        - `runtime (Union[LambdaRuntime, PythonRuntime, DockerRuntime])`: The runtime environment for the Lambda function. Defaults to Python runtime.
        - `domain (Optional[str])`: Optional custom domain. Currently unsupported, will raise an exception if provided.
        - `build_directory (str)`: The directory to build the Lambda function from. Defaults to the current directory.
        - `build_ignore (List[str])`: A list of files or directories to ignore during the build process. Defaults to an empty list.
        """
        if domain is not None:
            raise exceptions.ComingSoon(issue_number=71)
        if isinstance(runtime, DockerRuntime):
            raise exceptions.ComingSoon(issue_number=72)

        if isinstance(handler, Callable):  # type: ignore
            handler = _get_relative_handler_import_path(handler)  # type: ignore

        build_diff_args: Dict[str, Any] = {
            "handler": handler,
            "runtime": runtime.value
            if isinstance(runtime, LambdaRuntime)
            else runtime.runtime.value,
            "build_local": True,  # TODO: Remove this when we can support remote builds
        }
        if env is not None:
            build_diff_args["env"] = env
        if (
            isinstance(runtime, PythonRuntime)
            and runtime.requirements_txt_path is not None
        ):
            build_diff_args["requirements_txt_path"] = runtime.requirements_txt_path

        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args=build_diff_args,
        )
        resource_id_with_launchflow_prefix = f"{name}-{lf.project}-{lf.environment}"

        self._lambda_function = LambdaFunction(
            name,
            timeout_seconds=timeout_seconds,
            memory_size_mb=memory_size_mb,
            package_type="Zip",  # TODO: Support Docker
            runtime=runtime if isinstance(runtime, LambdaRuntime) else runtime.runtime,
        )
        self._lambda_function.resource_id = resource_id_with_launchflow_prefix

        self._lambda_function_url = None
        if isinstance(url, LambdaURL):
            self._lambda_function_url = LambdaFunctionURL(
                f"{name}-url",
                function=self._lambda_function,
                authorization="NONE" if url.public else "AWS_IAM",
                cors=url.cors,
            )

        self._api_gateway_route = None
        self._api_gateway_integration = None
        if isinstance(url, APIGatewayURL):
            self._api_gateway_integration = APIGatewayLambdaIntegration(
                f"{name}-integration",
                api_gateway=url.api_gateway,
                function=self._lambda_function,
            )
            self._api_gateway_route = APIGatewayRoute(
                f"{name}-route",
                api_gateway=url.api_gateway,
                route_key=url.route_key,
                authorization="NONE" if url.public else "AWS_IAM",
                api_gateway_integration=self._api_gateway_integration,
            )

        self.url = url
        self.runtime_options = runtime
        self.env = env or {}
        self.handler = handler

    def inputs(self) -> LambdaServiceInputs:
        return LambdaServiceInputs()

    def resources(self) -> List[Resource]:
        to_return: List[Resource] = [self._lambda_function]
        if self._lambda_function_url is not None:
            to_return.append(self._lambda_function_url)
        if self._api_gateway_route is not None:
            to_return.append(self._api_gateway_route)
        if self._api_gateway_integration is not None:
            to_return.append(self._api_gateway_integration)
        return to_return

    def outputs(self) -> ServiceOutputs:
        try:
            lambda_outputs = self._lambda_function.outputs()
            if (
                isinstance(self.url, LambdaURL)
                and self._lambda_function_url is not None
            ):
                lambda_url_outputs = self._lambda_function_url.outputs()
                service_url = lambda_url_outputs.function_url
            elif isinstance(self.url, APIGatewayURL):
                api_gateway_outputs = self.url.api_gateway.outputs()
                service_url = (
                    f"{api_gateway_outputs.api_gateway_endpoint}{self.url.path}"
                )
            else:
                raise exceptions.ServiceOutputsNotFound(service_name=self.name)
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_outputs = ServiceOutputs(
            service_url=service_url,
            # TODO: Support custom domains for Lambda
            dns_outputs=None,
        )
        service_outputs.aws_arn = lambda_outputs.aws_arn

        return service_outputs

    async def _build(
        self,
        *,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool = True,
    ) -> LambdaServiceReleaseInputs:
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()

        if self.handler == "TODO":
            # TODO: Add runtime-specific validation for the handler. Different runtimes have different requirements.
            raise ValueError(
                "Invalid handler: `TODO`. Please provide a valid handler path for the Lambda function."
            )

        lambda_client = boto3.client(
            "lambda", region_name=aws_environment_config.region
        )

        lambda_function_outputs = self._lambda_function.outputs()

        python_version = None
        requirements_txt_path = None
        if isinstance(self.runtime_options, PythonRuntime):
            python_version = self.runtime_options.runtime.python_version()
            requirements_txt_path = self.runtime_options.requirements_txt_path

        zip_file_content = _zip_source(
            build_directory=self.build_directory,
            build_ignore=self.build_ignore,
            python_version=python_version,
            requirements_txt_path=requirements_txt_path,
        )

        _ = lambda_client.update_function_configuration(
            FunctionName=lambda_function_outputs.function_name,
            Handler=self.handler,  # type: ignore
            Environment={
                "Variables": {
                    "LAUNCHFLOW_PROJECT": launchflow_uri.project_name,
                    "LAUNCHFLOW_ENVIRONMENT": launchflow_uri.environment_name,
                    "LAUNCHFLOW_CLOUD_PROVIDER": "aws",
                    "LAUNCHFLOW_DEPLOYMENT_ID": deployment_id,
                    "LAUNCHFLOW_ARTIFACT_BUCKET": f"s3://{aws_environment_config.artifact_bucket}",
                    **self.env,
                }
            },
        )

        # Wait for the configuration update to finish before publishing a new version
        lambda_client.get_waiter("function_updated").wait(
            FunctionName=lambda_function_outputs.function_name
        )

        # Try to update the existing function
        response = lambda_client.update_function_code(
            FunctionName=lambda_function_outputs.function_name,
            Publish=True,
            ZipFile=zip_file_content,
            # TODO: Support Docker
        )
        function_version = response["Version"]

        # Wait for the function to be active before returning the version
        lambda_client.get_waiter("function_active").wait(
            FunctionName=lambda_function_outputs.function_name,
            Qualifier=function_version,
        )

        return LambdaServiceReleaseInputs(function_version=function_version)

    async def _promote(
        self,
        *,
        from_aws_environment_config: AWSEnvironmentConfig,
        to_aws_environment_config: AWSEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,
        promote_local: bool = True,
    ) -> LambdaServiceReleaseInputs:
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()

        from_lambda_outputs = self._lambda_function.outputs(
            project=from_launchflow_uri.project_name,
            environment=from_launchflow_uri.environment_name,
        )
        to_lambda_outputs = self._lambda_function.outputs(
            project=to_launchflow_uri.project_name,
            environment=to_launchflow_uri.environment_name,
        )

        from_lambda_client = boto3.client(
            "lambda", region_name=from_aws_environment_config.region
        )
        to_lambda_client = boto3.client(
            "lambda", region_name=to_aws_environment_config.region
        )

        # Downloads the zip file of the function version
        get_function_response = from_lambda_client.get_function(
            FunctionName=from_lambda_outputs.function_name,
            Qualifier=from_lambda_outputs.alias_name,
        )
        function_zip_file = get_function_response["Code"]["Location"]  # type: ignore

        source_code = requests.get(function_zip_file).content

        # Updates the DEPLOYMENT_ID environment variable
        _ = to_lambda_client.update_function_configuration(
            FunctionName=to_lambda_outputs.function_name,
            Environment={
                "Variables": {
                    "LAUNCHFLOW_PROJECT": to_launchflow_uri.project_name,
                    "LAUNCHFLOW_ENVIRONMENT": to_launchflow_uri.environment_name,
                    "LAUNCHFLOW_CLOUD_PROVIDER": "aws",
                    "LAUNCHFLOW_DEPLOYMENT_ID": to_deployment_id,
                    "LAUNCHFLOW_ARTIFACT_BUCKET": f"s3://{to_aws_environment_config.artifact_bucket}",
                    **self.env,
                }
            },
        )

        # Wait for the configuration update to finish before publishing a new version
        to_lambda_client.get_waiter("function_updated").wait(
            FunctionName=to_lambda_outputs.function_name
        )

        # Uploads the zip file to the new environment
        update_code_response = to_lambda_client.update_function_code(
            FunctionName=to_lambda_outputs.function_name,
            ZipFile=source_code,
            Publish=True,
        )

        # Returns the new function version
        function_version = update_code_response["Version"]

        return LambdaServiceReleaseInputs(function_version=function_version)

    async def _release(
        self,
        *,
        release_inputs: LambdaServiceReleaseInputs,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ) -> None:
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()

        lambda_outputs = self._lambda_function.outputs()

        lambda_client = boto3.client(
            "lambda", region_name=aws_environment_config.region
        )

        lambda_client.update_alias(
            FunctionName=lambda_outputs.function_name,
            Name=lambda_outputs.alias_name,
            FunctionVersion=release_inputs.function_version,
        )
