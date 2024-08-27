import dataclasses
from typing import List, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class FirebaseProjectOutputs(Outputs):
    pass


@dataclasses.dataclass
class FirebaseProjectInputs(ResourceInputs):
    pass


# TODO: Update docstring
class FirebaseProject(GCPResource[FirebaseProjectOutputs]):
    product = ResourceProduct.GCP_FIREBASE_PROJECT.value

    def __init__(self, name: str) -> None:
        """Create a new Firebase Project resource.
        **Args:**
        - `name (str)`: The name of the Firebase project.
        """
        super().__init__(name=name)
        # public metadata

    def inputs(self, environment_state: EnvironmentState) -> FirebaseProjectInputs:
        return FirebaseProjectInputs(resource_id=self.resource_id)


@dataclasses.dataclass
class FirebaseHostingSiteOutputs(Outputs):
    default_url: str
    desired_dns_records: List[str]


@dataclasses.dataclass
class FirebaseHostingSiteInputs(ResourceInputs):
    firebase_project_id: str
    # TODO: Reconcile args with other usage of domains
    custom_domain: Optional[str]


class FirebaseHostingSite(GCPResource[FirebaseHostingSiteOutputs]):
    product = ResourceProduct.GCP_FIREBASE_HOSTING_SITE.value

    def __init__(
        self,
        name: str,
        *,
        firebase_project: FirebaseProject,
        custom_domain: Optional[str] = None,
    ) -> None:
        """Create a new Firebase Hosting Site resource.
        **Args:**
        - `name (str)`: The name of the Firebase site.
        """
        super().__init__(name=name)
        # public metadata
        self.firebase_project = firebase_project
        self.custom_domain = custom_domain

    def inputs(self, environment_state: EnvironmentState) -> FirebaseHostingSiteInputs:
        firebase_project_id = Depends(self.firebase_project).gcp_id  # type: ignore
        return FirebaseHostingSiteInputs(
            resource_id=self.resource_id,
            firebase_project_id=firebase_project_id,
            custom_domain=self.custom_domain,
        )
