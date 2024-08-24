import logging
import sys
from typing import Dict, List, Tuple

from launchflow import exceptions
from launchflow.cli.utils import import_from_string
from launchflow.deployment import Deployment


def deduplicate_deployments(deployments: Tuple[Deployment]) -> List[Deployment]:
    """
    Deduplicate deployments based on matching name and product name.

    Args:
    - `deployments`: The deployments to deduplicate.

    Returns:
    - The deduplicated deployments.
    """
    deployment_dict: Dict[str, Deployment] = {}

    for deployment in deployments:
        if deployment.name in deployment_dict:
            existing_resource = deployment_dict[deployment.name]
            if existing_resource.product != deployment.product:
                raise exceptions.DuplicateDeploymentProductMismatch(
                    deployment_name=deployment.name,
                    existing_product=existing_resource.product,
                    new_product=deployment.product,
                )
        deployment_dict[deployment.name] = deployment

    return list(deployment_dict.values())


def import_deployments(deployment_import_strs: List[str]) -> List[Deployment]:
    sys.path.insert(0, "")
    deployments: List[Deployment] = []
    for deployment_str in deployment_import_strs:
        try:
            imported_deployment = import_from_string(deployment_str)
        except AttributeError:
            logging.debug("Failed to import resource %s", deployment_str)
            continue
        if not isinstance(imported_deployment, Deployment):
            raise ValueError(
                f"Deployment {imported_deployment} is not a valid Deployment"
            )
        deployments.append(imported_deployment)
    return deployments
