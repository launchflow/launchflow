import logging
import sys
from typing import Dict, List, Tuple

from launchflow import exceptions
from launchflow.aws.secrets_manager import SecretsManagerSecret
from launchflow.cli.utils import import_from_string
from launchflow.docker.resource import DockerResource
from launchflow.gcp.secret_manager import SecretManagerSecret
from launchflow.resource import Resource

# TODO: move this file to lf.utils submodule in its own file


def deduplicate_resources(resources: Tuple[Resource]) -> List[Resource]:
    """
    Deduplicate resources based on matching name and product name.

    Args:
    - `resources`: The resources to deduplicate.

    Returns:
    - The deduplicated resources.
    """
    resource_dict: Dict[str, Resource] = {}

    for resource in resources:
        if resource.name in resource_dict:
            existing_resource = resource_dict[resource.name]
            if existing_resource.product != resource.product:
                raise exceptions.DuplicateResourceProductMismatch(
                    resource_name=resource.name,
                    existing_product=existing_resource.product,
                    new_product=resource.product,
                )
        resource_dict[resource.name] = resource

    return list(resource_dict.values())


def import_resources(resource_import_strs: List[str]) -> List[Resource]:
    sys.path.insert(0, "")
    resources: List[Resource] = []
    for resource_str in resource_import_strs:
        try:
            imported_resource = import_from_string(resource_str)
        except AttributeError:
            logging.debug("Failed to import resource %s", resource_str)
            continue
        if not isinstance(imported_resource, Resource):
            continue
        resources.append(imported_resource)
    return resources


# TODO: Consider replacing all instances of this with the isinstance check directly
def is_local_resource(resource: Resource) -> bool:
    if isinstance(resource, DockerResource):
        return True

    return False


def is_secret_resource(resource: Resource) -> bool:
    return isinstance(resource, SecretsManagerSecret) or isinstance(
        resource, SecretManagerSecret
    )
