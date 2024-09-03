import sys
from typing import Dict, List, Tuple

from launchflow import exceptions
from launchflow.cli.utils import import_from_string
from launchflow.logger import logger
from launchflow.service import Service


def deduplicate_services(services: Tuple[Service]) -> List[Service]:
    """
    Deduplicate services based on matching name and product name.

    Args:
    - `services`: The services to deduplicate.

    Returns:
    - The deduplicated resources.
    """
    service_dict: Dict[str, Service] = {}

    for service in services:
        if service.name in service_dict:
            existing_resource = service_dict[service.name]
            if existing_resource.product != service.product:
                raise exceptions.DuplicateServiceProductMismatch(
                    service_name=service.name,
                    existing_product=existing_resource.product,
                    new_product=service.product,
                )
        service_dict[service.name] = service

    return list(service_dict.values())


def import_services(service_import_strs: List[str]) -> List[Service]:
    sys.path.insert(0, "")
    services: List[Service] = []
    for service_str in service_import_strs:
        try:
            imported_service = import_from_string(service_str)
        except AttributeError as e:
            logger.debug(
                "Failed to import resource %s, %s",
                service_str,
                e,
                exc_info=True,
            )
            continue
        if not isinstance(imported_service, Service):
            raise ValueError(f"Service {imported_service} is not a valid Service")
        services.append(imported_service)
    return services
