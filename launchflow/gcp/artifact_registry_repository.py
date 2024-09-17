from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Union

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclass
class ArtifactRegistryOutputs(Outputs):
    # NOTE: This is only set if the format is DOCKER
    docker_repository: Optional[str] = None


@dataclass
class ArtifactRegistryInputs(ResourceInputs):
    format: str
    location: Optional[str] = None


class RegistryFormat(Enum):
    DOCKER = "DOCKER"
    MAVEN = "MAVEN"
    NPM = "NPM"
    PYTHON = "PYTHON"
    APT = "APT"
    YUM = "YUM"
    KUBEFLOW = "KUBEFLOW"
    GENERIC = "GENERIC"


class ArtifactRegistryRepository(GCPResource[ArtifactRegistryOutputs]):
    """A resource for creating an artifact registry repository.
    Can be used to store docker images, python packages, and more.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    ### Example Usage

    #### Create a docker repository
    ```python
    import launchflow as lf

    artifact_registry = lf.gcp.ArtifactRegistryRepository("my-artifact-registry", format="DOCKER")
    ```

    #### Create a python repository
    ```python
    import launchflow as lf

    python_repository = lf.gcp.ArtifactRegistryRepository("my-python-repository", format="PYTHON")
    ```

    #### Create a NPM repository
    ```python
    import launchflow as lf

    npm_repository = lf.gcp.ArtifactRegistryRepository("my-npm-repository", format="NPM")
    ```
    """

    product = ResourceProduct.GCP_ARTIFACT_REGISTRY_REPOSITORY.value

    def __init__(
        self,
        name: str,
        format: Union[str, RegistryFormat],
        location: Optional[str] = None,
    ) -> None:
        """Create a new ArtifactRegistryRepository resource.

        **Args:**
        - `name (str)`: The name of the ArtifactRegistryRepository resource. This must be globally unique.
        - `format (Union[str, RegistryFormat])`: The format of the ArtifactRegistryRepository.
        - `location (Optional[str])`: The location of the ArtifactRegistryRepository. Defaults to the default region of the GCP project.
        """
        super().__init__(
            name=name,
            replacement_arguments={"format", "location"},
        )
        if isinstance(format, str):
            format = RegistryFormat(format.upper())
        self.format = format
        self.location = location

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        location = self.location or environment_state.gcp_config.default_region  # type: ignore
        return {
            "google_artifact_registry_repository.repository": f"projects/{environment_state.gcp_config.project_id}/locations/{location}/repositories/{self.resource_id}",  # type: ignore
        }

    def inputs(self, environment_state: EnvironmentState) -> ArtifactRegistryInputs:
        return ArtifactRegistryInputs(
            resource_id=self.resource_id,
            format=self.format.value,
            location=self.location,
        )
