import enum
from dataclasses import dataclass
from typing import Literal, Optional

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.aws.shared import CORS
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


class LambdaRuntime(enum.Enum):
    PYTHON2_7 = "python2.7"
    PYTHON3_6 = "python3.6"
    PYTHON3_7 = "python3.7"
    PYTHON3_8 = "python3.8"
    PYTHON3_9 = "python3.9"
    PYTHON3_10 = "python3.10"
    PYTHON3_11 = "python3.11"
    PYTHON3_12 = "python3.12"
    NODEJS = "nodejs"
    NODEJS4_3 = "nodejs4.3"
    NODEJS6_10 = "nodejs6.10"
    NODEJS8_10 = "nodejs8.10"
    NODEJS10_X = "nodejs10.x"
    NODEJS12_X = "nodejs12.x"
    NODEJS14_X = "nodejs14.x"
    NODEJS16_X = "nodejs16.x"
    NODEJS18_X = "nodejs18.x"
    NODEJS20_X = "nodejs20.x"
    NODEJS4_3_EDGE = "nodejs4.3-edge"
    JAVA8 = "java8"
    JAVA8_AL2 = "java8.al2"
    JAVA11 = "java11"
    JAVA17 = "java17"
    JAVA21 = "java21"
    DOTNETCORE1_0 = "dotnetcore1.0"
    DOTNETCORE2_0 = "dotnetcore2.0"
    DOTNETCORE2_1 = "dotnetcore2.1"
    DOTNETCORE3_1 = "dotnetcore3.1"
    DOTNET6 = "dotnet6"
    DOTNET8 = "dotnet8"
    GO1_X = "go1.x"
    RUBY2_5 = "ruby2.5"
    RUBY2_7 = "ruby2.7"
    RUBY3_2 = "ruby3.2"
    RUBY3_3 = "ruby3.3"
    PROVIDED = "provided"
    PROVIDED_AL2 = "provided.al2"
    PROVIDED_AL2023 = "provided.al2023"

    def python_version(self) -> Optional[str]:
        if self in [
            LambdaRuntime.PYTHON2_7,
            LambdaRuntime.PYTHON3_6,
            LambdaRuntime.PYTHON3_7,
            LambdaRuntime.PYTHON3_8,
            LambdaRuntime.PYTHON3_9,
            LambdaRuntime.PYTHON3_10,
            LambdaRuntime.PYTHON3_11,
            LambdaRuntime.PYTHON3_12,
        ]:
            return self.value.split("python")[-1]
        return None


@dataclass
class LambdaFunctionInputs(ResourceInputs):
    timeout_seconds: int
    memory_size_mb: int
    package_type: Literal["Image", "Zip"]
    runtime: Optional[LambdaRuntime]


@dataclass
class LambdaFunctionOutputs(Outputs):
    function_name: str
    alias_name: str


class LambdaFunction(AWSResource[LambdaFunctionOutputs]):
    """A Lambda function.

    ### Example Usage
    ```python
    import launchflow as lf

    lambda_func = lf.aws.LambdaFunction("my-lambda-function")
    ```
    """

    product = ResourceProduct.AWS_LAMBDA_FUNCTION.value

    def __init__(
        self,
        name: str,
        *,
        timeout_seconds: int = 10,
        memory_size_mb: int = 256,
        package_type: Literal["Image", "Zip"] = "Zip",
        runtime: Optional[LambdaRuntime] = LambdaRuntime.PYTHON3_11,
    ) -> None:
        """Create a new Lambda Function.

        **Args:**
        - `name (str)`: The name of the Lambda Function.
        - `timeout_seconds (int)`: The number of seconds before the Lambda function times out.
        - `memory_size_mb (int)`: The amount of memory in MB allocated to the Lambda function.
        - `package_type (Literal["Image", "Zip"])`: The type of package for the Lambda function.
        - `runtime (Optional[LambdaRuntime])`: The runtime for the Lambda function.

        **Raises:**
        - `ValueError`: If `runtime` is `None` and `package_type` is "Zip".
        """
        if runtime is None and package_type == "Zip":
            raise ValueError(
                '`runtime` argument is required when `package_type` is "Zip"'
            )
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
            replacement_arguments={"package_type"},
        )
        self.timeout_seconds = timeout_seconds
        self.memory_size_mb = memory_size_mb
        self.package_type = package_type
        self.runtime = runtime

    def inputs(self, environment_state: EnvironmentState) -> LambdaFunctionInputs:
        return LambdaFunctionInputs(
            resource_id=self.resource_id,
            timeout_seconds=self.timeout_seconds,
            memory_size_mb=self.memory_size_mb,
            package_type=self.package_type,
            runtime=self.runtime,
        )


@dataclass
class LambdaFunctionURLInputs(ResourceInputs):
    function_arn: str
    function_alias: str
    authorization: Literal["AWS_IAM", "NONE"]
    cors: Optional[CORS]


@dataclass
class LambdaFunctionURLOutputs(Outputs):
    function_url: str
    url_id: str


class LambdaFunctionURL(AWSResource[LambdaFunctionURLOutputs]):
    """A Lambda function URL.

    ### Example Usage
    ```python
    import launchflow as lf

    function = lf.aws.LambdaFunction("my-lambda-function")
    function_url = lf.aws.LambdaFunctionURL("my-lambda-url", function=function)
    ```
    """

    product = ResourceProduct.AWS_LAMBDA_FUNCTION_URL.value

    def __init__(
        self,
        name: str,
        *,
        function: LambdaFunction,
        authorization: Literal["AWS_IAM", "NONE"] = "NONE",  # NONE == public
        cors: Optional[CORS] = None,
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.function = function
        self.authorization = authorization
        self.cors = cors

    def inputs(self, environment_state: EnvironmentState) -> LambdaFunctionURLInputs:
        return LambdaFunctionURLInputs(
            resource_id=self.resource_id,
            function_arn=Depends(self.function).aws_arn,  # type: ignore
            function_alias=Depends(self.function).alias_name,  # type: ignore
            authorization=self.authorization,  # type: ignore
            cors=self.cors,
        )
