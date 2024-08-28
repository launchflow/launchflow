from dataclasses import dataclass
from typing import Literal, Optional

import launchflow as lf
from launchflow.aws.alb import ApplicationLoadBalancer
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
    port: int = 80
    memory_size: int = 256
    timeout: int = 10
    alb_security_group_id: Optional[str] = None
    alb_target_group_arn: Optional[str] = None
    package_type: Literal["Image", "Zip"] = "Image"


@dataclass
class LambdaServiceContainerOutputs(Outputs):
    lambda_url: str


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
        hack="",
        # ecs_cluster: Union[ECSCluster, str],
        alb: Optional[ApplicationLoadBalancer] = None,
        package_type: Literal["Image", "Zip"] = "Zip",
        # cpu: int = 256,
        memory: int = 256,
        port: int = 80,
        timeout: int = 10,
        # desired_count: int = 1,
    ) -> None:
        """TODO"""
        if not isinstance(alb, (ApplicationLoadBalancer, type(None))):
            raise ValueError("alb must be an ApplicationLoadBalancer or None")

        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.alb = alb
        self.package_type = package_type
        self.port = port
        self.memory = memory
        self.timeout = timeout

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
            package_type=self.package_type,
            port=self.port,
            memory_size=self.memory,
            timeout=self.timeout,
            hack=self.hack,
        )
