from dataclasses import dataclass

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class ECSClusterInputs(ResourceInputs):
    pass


@dataclass
class ECSClusterOutputs(Outputs):
    cluster_name: str


class ECSCluster(AWSResource[ECSClusterOutputs]):
    """An ECS cluster.

    ****Example usage:****
    ```python
    import launchflow as lf

    ecs_cluster = lf.aws.ECSCluster("my-cluster")
    ```
    """

    product = ResourceProduct.AWS_ECS_CLUSTER.value

    def __init__(self, name: str) -> None:
        """Creates a new ECS cluster.

        **Args:**
        - `name (str)`: The name of the ECS cluster.
        """
        super().__init__(name=name, resource_id=f"{name}-{lf.project}-{lf.environment}")

    def inputs(self, environment_state: EnvironmentState) -> ECSClusterInputs:
        """Get the inputs for the ECS cluster resource.

        **Args:**
        - `environment_state (EnvironmentState)`: The environment to get inputs for.

        **Returns:**
        - An `ECSClusterInputs` object containing the inputs for the ECS cluster.
        """
        return ECSClusterInputs(resource_id=self.resource_id)
