from dataclasses import dataclass

from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class ACMCertificateInputs(ResourceInputs):
    domain_name: str


@dataclass
class ACMCertificateOutputs(Outputs):
    domain_name: str


class ACMCertificate(AWSResource[ACMCertificateOutputs]):
    """An ACM Certificate resource.

    **Note:** This Resource is in beta and is likely to change in the future.

    For more information see [the official documentation](https://docs.aws.amazon.com/acm/).

    ### Example Usage
    ```python
    import launchflow as lf

    certificate = lf.aws.ACMCertificate("my-certificate")
    ```
    """

    product = ResourceProduct.AWS_ACM_CERTIFICATE.value

    def __init__(
        self,
        name: str,
        domain_name: str,
    ) -> None:
        """Creates a new ACM Certificate resource.

        **Args:**
        - `name (str)`: The name of the resource.
        - `domain_name (str)`: The domain name to use for the certificate.
        """
        super().__init__(name=name)
        self.domain_name = domain_name

    def inputs(self, environment_state: EnvironmentState) -> ACMCertificateInputs:
        return ACMCertificateInputs(
            resource_id=self.resource_id,
            domain_name=self.domain_name,
        )
