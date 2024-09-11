from typing import Any, Dict, Union

import deepdiff  # type: ignore
import rich
import yaml

from launchflow.backend import LaunchFlowBackend
from launchflow.config import config
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.resource import Resource
from launchflow.service import Service

RESOURCE_COLOR = "light_goldenrod3"
SERVICE_COLOR = "blue"
ENVIRONMENT_COLOR = "bold purple"
OP_COLOR = "bold pale_green3"
DEPENDS_ON_COLOR = "yellow"


class ResourceRef:
    def __init__(self, resource: Resource):
        self.resource = resource

    def __str__(self):
        return f"[{RESOURCE_COLOR}]{self.resource}[/{RESOURCE_COLOR}]"


class ServiceRef:
    def __init__(self, service: Service):
        self.service = service

    def __str__(self):
        return f"[{SERVICE_COLOR}]{self.service}[/{SERVICE_COLOR}]"


class EnvironmentRef:
    def __init__(
        self,
        manager: Union[EnvironmentManager, ServiceManager, ResourceManager],
        show_backend: bool = True,
    ):
        self.manager = manager
        self.show_backend = show_backend

    def __str__(self):
        backend_prefix = ""
        backend = config.backend
        if self.show_backend and backend is not None:
            backend_prefix = backend.to_str() + "/"
            if isinstance(backend, LaunchFlowBackend):
                backend_prefix = backend_prefix.replace(
                    "default", config.get_account_id()
                )

        return f"[{ENVIRONMENT_COLOR}]{backend_prefix}{self.manager.project_name}/{self.manager.environment_name}[/{ENVIRONMENT_COLOR}]"


def dump_verbose_logs(logs_file: str, title: str):
    rich.print(f"───── {title} ─────")
    with open(logs_file, "r") as f:
        print(f.read())
    rich.print(f"───── End of {title} ─────\n")


def format_configuration_dict(configuration_dict: Dict[str, Any]):
    return yaml.safe_dump(configuration_dict).replace("'", "")


def compare_dicts(d1, d2):
    diff = deepdiff.DeepDiff(d1, d2, ignore_order=True)
    diff_keys = diff.affected_root_keys
    diff_strs = []
    for key in diff_keys:
        old_value = d1.get(key)
        new_value = d2.get(key)
        diff_strs.append(f"[cyan]{key}[/cyan]: {old_value} -> {new_value}")

    if diff_strs:
        return "    " + "\n    ".join(diff_strs)
    return ""
