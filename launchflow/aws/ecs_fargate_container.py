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
class ECSFargateServiceContainerInputs(ResourceInputs):
    resource_name: str
    ecs_cluster_name: str
    port: int = 80
    desired_count: int = 1
    alb_security_group_id: Optional[str] = None
    alb_target_group_arn: Optional[str] = None


@dataclass
class ECSFargateServiceContainerOutputs(Outputs):
    public_ip: str


class ECSFargateServiceContainer(AWSResource[ECSFargateServiceContainerOutputs]):
    """A container for a service running on ECS Fargate.

    ### Example Usage
    ```python
    import launchflow as lf

    service_container = lf.aws.ECSFargateServiceContainer("my-service-container")
    ```
    """

    product = ResourceProduct.AWS_ECS_FARGATE_SERVICE_CONTAINER.value

    def __init__(
        self,
        name: str,
        ecs_cluster: Union[ECSCluster, str],
        alb: Optional[ApplicationLoadBalancer] = None,
        port: int = 80,
        desired_count: int = 1,
    ) -> None:
        """Creates a new ECS Fargate service container.

        **Args:**
        - `name (str)`: The name of the ECS Fargate service container.
        - `ecs_cluster (Union[ECSCluster, str])`: The ECS cluster or the name of the ECS cluster.
        - `port (int)`: The port the container listens on. Defaults to 80.
        - `desired_count (int)`: The number of tasks to run. Defaults to 1.

        **Raises:**
         - `ValueError`: If `ecs_cluster` is not an instance of `ECSCluster` or `str`.
        """
        if not isinstance(ecs_cluster, (ECSCluster, str)):
            raise ValueError("ecs_cluster must be an ECSCluster or a str")
        if not isinstance(alb, (ApplicationLoadBalancer, type(None))):
            raise ValueError("alb must be an ApplicationLoadBalancer or None")

        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.ecs_cluster = ecs_cluster
        self.alb = alb
        self.port = port
        self.desired_count = desired_count

    def inputs(
        self, environment_state: EnvironmentState
    ) -> ECSFargateServiceContainerInputs:
        if isinstance(self.ecs_cluster, ECSCluster):
            ecs_cluster_name = Depends(  # type: ignore
                self.ecs_cluster
            ).cluster_name  # type: ignore
        elif isinstance(self.ecs_cluster, str):
            ecs_cluster_name = self.ecs_cluster
        else:
            raise ValueError("cluster must be an ECSCluster or a str")

        alb_security_group_id = None
        alb_target_group_arn = None
        if self.alb is not None:
            alb_security_group_id = Depends(self.alb).alb_security_group_id  # type: ignore
            alb_target_group_arn = Depends(self.alb).alb_target_group_arn  # type: ignore

        return ECSFargateServiceContainerInputs(
            resource_id=self.resource_id,
            resource_name=self.name,
            ecs_cluster_name=ecs_cluster_name,
            port=self.port,
            desired_count=self.desired_count,
            alb_security_group_id=alb_security_group_id,
            alb_target_group_arn=alb_target_group_arn,
        )
