from dataclasses import dataclass
from typing import Literal

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class ECRRepositoryOutputs(Outputs):
    repository_url: str


@dataclass
class ECRRepositoryInputs(ResourceInputs):
    force_delete: bool
    image_tag_mutability: Literal["MUTABLE", "IMMUTABLE"]


class ECRRepository(AWSResource[ECRRepositoryOutputs]):
    """A resource for creating an ECR repository.
    Can be used to store container images.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    ### Example Usage
    ```python
    import launchflow as lf

    ecr_repository = lf.aws.ECRRepository("my-ecr-repository")
    ```
    """

    product = ResourceProduct.AWS_ECR_REPOSITORY.value

    def __init__(
        self,
        name: str,
        force_delete: bool = True,
        image_tag_mutability: Literal["MUTABLE", "IMMUTABLE"] = "MUTABLE",
    ) -> None:
        """Create a new ECRRepository resource.

        **Args:**
        - `name (str)`: The name of the ECRRepository resource. This must be globally unique.
        - `force_delete (bool)`: Whether to force delete the repository when the environment is deleted. Defaults to True.
        - `image_tag_mutability (Literal["MUTABLE", "IMMUTABLE"])`: The image tag mutability for the repository. Defaults to "MUTABLE"
        """
        super().__init__(
            name=name,
            replacement_arguments={"format", "location"},
            resource_id=f"{name}-{lf.project}-{lf.environment}".lower(),
        )
        self.force_delete = force_delete
        self.image_tag_mutability = image_tag_mutability

    def inputs(self, environment_state: EnvironmentState) -> ECRRepositoryInputs:
        return ECRRepositoryInputs(
            resource_id=self.resource_id,
            force_delete=self.force_delete,
            image_tag_mutability=self.image_tag_mutability,
        )
