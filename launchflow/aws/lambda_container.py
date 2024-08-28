from dataclasses import dataclass
from typing import Optional, Union

import launchflow as lf
from launchflow.aws.alb import ApplicationLoadBalancer
from launchflow.aws.ecs_cluster import ECSCluster
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclass
class LambdaServiceContainerInputs(ResourceInputs):
    # resource_name: str
    # ecs_cluster_name: str
    # cpu: int = 256
    # memory: int = 512
    # port: int = 80
    # desired_count: int = 1
    hack: str
    alb_security_group_id: Optional[str] = None
    alb_target_group_arn: Optional[str] = None


@dataclass
class LambdaServiceContainerOutputs(Outputs):
    pass
    # public_ip: str


class LambdaServiceContainer(AWSResource[LambdaServiceContainerOutputs]):
    """A container for a service running on Lambda.

    ****Example usage:****
    ```python
    import launchflow as lf

    service_container = lf.aws.LambdaServiceContainer("my-service-container")
    ```
    """

    product = ResourceProduct.AWS_LAMBDA_SERVICE_CONTAINER.value

    def __init__(
        self,
        name: str,
        hack = "",
        # ecs_cluster: Union[ECSCluster, str],
        alb: Optional[ApplicationLoadBalancer] = None,
        # cpu: int = 256,
        # memory: int = 512,
        port: int = 80,
        # desired_count: int = 1,
    ) -> None:
        """TODO
        """
        if not isinstance(alb, (ApplicationLoadBalancer, type(None))):
            raise ValueError("alb must be an ApplicationLoadBalancer or None")

        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.alb = alb
        self.hack = hack

    def inputs(
        self, environment_state: EnvironmentState
    ) -> LambdaServiceContainerInputs:
        """Get the inputs for the ECS Fargate service container resource.

        **Args:**
         - `environment_state (EnvironmentState)`: The environment to get inputs for

        **Returns:**
         - `LambdaServiceContainerInputs`: The inputs required for the ECS Fargate service container.
        """

        alb_security_group_id = None
        alb_target_group_arn = None
        if self.alb is not None:
            alb_security_group_id = Depends(self.alb).alb_security_group_id  # type: ignore
            alb_target_group_arn = Depends(self.alb).alb_target_group_arn  # type: ignore

        return LambdaServiceContainerInputs(
            resource_id=self.resource_id,
            alb_security_group_id=alb_security_group_id,
            alb_target_group_arn=alb_target_group_arn,
            hack=self.hack,
        )
