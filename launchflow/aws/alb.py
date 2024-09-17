import hashlib
from dataclasses import dataclass
from typing import Optional

import launchflow as lf
from launchflow.aws.acm import ACMCertificate
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclass
class ApplicationLoadBalancerInputs(ResourceInputs):
    container_port: int
    health_check_path: Optional[str] = None
    domain_name: Optional[str] = None


@dataclass
class ApplicationLoadBalancerOutputs(Outputs):
    alb_target_group_arn: str
    alb_security_group_id: str
    alb_dns_name: str


class ApplicationLoadBalancer(AWSResource[ApplicationLoadBalancerOutputs]):
    """An Application Load Balancer.

    **Note:** This Resource is in beta and is likely to change in the future.

    For more information see [the official documentation](https://docs.aws.amazon.com/elasticloadbalancing/).

    ## Example Usage
    ```python
    import launchflow as lf

    alb = lf.aws.ApplicationLoadBalancer("my-lb", health_check_path='/health')
    ```
    """

    product = ResourceProduct.AWS_ALB.value

    def __init__(
        self,
        name: str,
        *,
        container_port: int = 80,
        health_check_path: Optional[str] = None,
        certificate: Optional[ACMCertificate] = None,
    ) -> None:
        """Creates a new Application Load Balancer.

        **Args:**
        - `name (str)`: The name of the Application Load Balancer.
        - `container_port (int)`: The port that the container listens on.
        - `health_check_path (Optional[str])`: The path to use for the health check
        - `certificate (Optional[ACMCertificate])`: The certificate to use for the ALB.
        """
        hash_id = hashlib.sha256(f"{lf.project}-{lf.environment}".encode()).hexdigest()[
            :5
        ]
        if len(name) > 27:
            id_name = name[:27]
        else:
            id_name = name
        resource_id = f"{id_name}-{hash_id}"
        super().__init__(name, resource_id=resource_id)
        self.container_port = container_port
        self.health_check_path = health_check_path
        self.certificate = certificate

    def inputs(
        self, environment_state: EnvironmentState
    ) -> ApplicationLoadBalancerInputs:
        domain_name = None
        if self.certificate:
            domain_name = Depends(self.certificate).domain_name  # type: ignore
        return ApplicationLoadBalancerInputs(
            resource_id=self.resource_id,
            container_port=self.container_port,
            health_check_path=self.health_check_path,
            domain_name=domain_name,
        )
