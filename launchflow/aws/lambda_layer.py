from dataclasses import dataclass
from typing import List

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class PythonLambdaLayerInputs(ResourceInputs):
    packages: List[str]


@dataclass
class PythonLambdaLayerOutputs(Outputs):
    pass


class PythonLambdaLayer(AWSResource[PythonLambdaLayerOutputs]):
    """A Lambda layer for Python.

    ****Example usage:****
    ```python
    import launchflow as lf

    layer = lf.aws.PythonLambdaLayer("my-lambda-layer", packages=["requests"])
    ```
    """

    product = ResourceProduct.AWS_PYTHON_LAMBDA_LAYER.value

    def __init__(
        self,
        name: str,
        *,
        packages: List[str],
    ) -> None:
        """TODO"""
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.packages = packages

    def inputs(self, environment_state: EnvironmentState) -> PythonLambdaLayerInputs:
        """Get the inputs for the Lambda layer.

        **Args:**
         - `environment_state (EnvironmentState)`: The environment to get inputs for

        **Returns:**
         - `PythonLambdaLayerInputs`: The inputs required for the Lambda layer
        """

        return PythonLambdaLayerInputs(
            resource_id=self.resource_id,
            packages=self.packages,
        )
