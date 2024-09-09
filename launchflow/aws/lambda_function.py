import enum
from dataclasses import dataclass
from typing import Literal, Optional

import launchflow as lf
from launchflow.aws.api_gateway import APIGateway
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs

"""
Use cases:
- Lambda inside / outside VPC (bool)  | punt

TODO
- Lambda publically accessible / private (pass in ALB, API Gateway, etc.)
- Lambda with / without internet access (pass in ENI, NAT Gateway, etc.)


- Lambda with custom triggers (e.g. S3, SQS, SNS, etc.)
- Lambda with container image vs zip (enum)
- Lambda with different runtimes, memory sizes, and timeouts (args)


TODO
- look into reasons to put Lambda in private vs public subnet

"""


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
class APIGatewayConfig(Inputs):
    api_gateway_id: str
    api_route_key: str


@dataclass
class LambdaFunctionInputs(ResourceInputs):
    # Shared Inputs
    timeout: int
    memory_size: int
    package_type: Literal["Image", "Zip"]
    # Static Inputs
    runtime: LambdaRuntime
    # API Gateway Inputs
    api_gateway_config: Optional[APIGatewayConfig]


@dataclass
class LambdaFunctionOutputs(Outputs):
    pass


class LambdaFunction(AWSResource[LambdaFunctionOutputs]):
    """A Lambda function.

    ****Example usage:****
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
        timeout: int = 10,
        memory_size: int = 256,
        package_type: Literal["Image", "Zip"] = "Zip",
        runtime: LambdaRuntime = LambdaRuntime.PYTHON3_11,
        route: Optional[str] = None,
        api_gateway: Optional[APIGateway] = None,
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.timeout = timeout
        self.memory_size = memory_size
        self.package_type = package_type
        self.runtime = runtime
        self.route = route

        self._api_gateway = api_gateway
        self.depends_on(api_gateway)  # type: ignore

    def inputs(self, environment_state: EnvironmentState) -> LambdaFunctionInputs:
        """Get the inputs for the Lambda function resource.

        **Args:**
         - `environment_state (EnvironmentState)`: The environment to get inputs for

        **Returns:**
         - `LambdaFunctionInputs`: The inputs required for the Lambda function resource
        """

        api_gateway_config = None
        if self._api_gateway is not None:
            api_gateway_id = Depends(self._api_gateway).api_gateway_id  # type: ignore
            # TODO: clean this up / throw validation error in __init__ if route is None and api_gateway is not None
            api_gateway_config = APIGatewayConfig(
                api_gateway_id=api_gateway_id,
                api_route_key=self.route or "/",
            )

        return LambdaFunctionInputs(
            resource_id=self.resource_id,
            timeout=self.timeout,
            memory_size=self.memory_size,
            package_type=self.package_type,
            runtime=self.runtime,
            api_gateway_config=api_gateway_config,
        )
