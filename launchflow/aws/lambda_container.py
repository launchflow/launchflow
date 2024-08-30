import enum
from dataclasses import dataclass
from typing import Literal, Optional

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
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
class LambdaContainerInputs(ResourceInputs):
    # Shared Inputs
    timeout: int = 10
    memory_size: int = 256
    package_type: Literal["Image", "Zip"] = "Image"
    # Static Inputs
    runtime: LambdaRuntime = LambdaRuntime.PYTHON3_11
    # Docker Inputs
    port: int = 80


# TODO: Pull API Gateway into its own Resource
@dataclass
class LambdaContainerOutputs(Outputs):
    lambda_url: str


class LambdaContainer(AWSResource[LambdaContainerOutputs]):
    """A container for a service running on Lambda.

    ****Example usage:****
    ```python
    import launchflow as lf

    lambda_func = lf.aws.LambdaServiceContainer("my-service-container")
    ```
    """

    product = ResourceProduct.AWS_LAMBDA_CONTAINER.value

    def __init__(
        self,
        name: str,
        *,
        timeout: int = 10,
        memory_size: int = 256,
        package_type: Literal["Image", "Zip"] = "Zip",
        runtime: LambdaRuntime = LambdaRuntime.PYTHON3_11,
        port: int = 80,
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
        self.port = port

    def inputs(self, environment_state: EnvironmentState) -> LambdaContainerInputs:
        """Get the inputs for the Lambda service container resource.

        **Args:**
         - `environment_state (EnvironmentState)`: The environment to get inputs for

        **Returns:**
         - `LambdaServiceContainerInputs`: The inputs required for the Lambda service container
        """

        return LambdaContainerInputs(
            resource_id=self.resource_id,
            timeout=self.timeout,
            memory_size=self.memory_size,
            package_type=self.package_type,
            runtime=self.runtime,
            port=self.port,
        )
