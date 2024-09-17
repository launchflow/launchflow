import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import yaml

from launchflow import exceptions
from launchflow.backend import (
    BackendOptions,
    GCSBackend,
    LaunchFlowBackend,
    LocalBackend,
    parse_backend_protocol_str,
)
from launchflow.validation import validate_environment_name, validate_project_name


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


@dataclass(frozen=True)
class LaunchFlowDotYaml:
    project: str
    backend: Union[LocalBackend, LaunchFlowBackend, GCSBackend]
    backend_options: BackendOptions
    default_environment: Optional[str]
    config_path: str
    ignore_roots: Optional[List[str]] = None

    def __post_init__(self):
        # validate the project and default environment if they are set
        if self.project:
            try:
                validate_project_name(self.project)
            except ValueError as e:
                raise exceptions.InvalidProjectNameInYaml(self.project, str(e))
        if self.default_environment:
            try:
                validate_environment_name(self.default_environment)
            except ValueError as e:
                raise exceptions.InvalidDefaultEnvironmentInYaml(
                    self.default_environment, str(e)
                )

    @property
    def project_directory_abs_path(self):
        return os.path.dirname(os.path.abspath(self.config_path))

    @classmethod
    def load_from_cwd(cls, start_path="."):
        file_path = _find_launchflow_yaml(start_path)
        if file_path is None:
            raise FileNotFoundError("Could not find 'launchflow.yaml' file.")
        return cls.load_from_file(file_path)

    @classmethod
    def load_from_file(cls, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
            project: Optional[str] = data.get("project")
            default_environment: Optional[str] = data.get("default_environment")
            backend_str: Optional[str] = data.get("backend")
            backend_options_dict: Dict[str, str] = data.get("backend_options", {})
            ignore_roots: Optional[List[str]] = data.get("ignore_roots")

        if project is None:
            raise ValueError("No project specified in the configuration.")
        if backend_str is None:
            raise ValueError("No backend specified in the configuration.")
        if not isinstance(backend_str, str):
            raise exceptions.InvalidBackend(
                f"Invalid backend: {backend_str}. It must be a string in the format `file://<path>` or `lf://<account_id>`."
            )

        # catch the parsing error
        try:
            backend_options = BackendOptions(**backend_options_dict)
        except TypeError:
            raise exceptions.InvalidBackend(
                f"Invalid backend options: {backend_options_dict}. It must be a yaml dict in the format: \n```\nbackend_options:\n  lf_backend_url: <url>\n```"
            )
        backend = parse_backend_protocol_str(backend_str, backend_options)

        return cls(
            project=project,
            backend=backend,  # type: ignore
            backend_options=backend_options,
            default_environment=default_environment,
            config_path=file_path,
            ignore_roots=ignore_roots,
        )

    def save(self):
        data = {
            "project": self.project,
            "backend": self.backend.to_str(),
        }
        if not self.backend_options.is_empty():
            data["backend_options"] = self.backend_options.to_dict()
        if self.default_environment is not None:
            data["default_environment"] = self.default_environment

        with open(self.config_path, "w") as file:
            yaml.dump(data, file, Dumper=Dumper, sort_keys=False)


def _find_launchflow_yaml(start_path="."):
    current_path = os.path.abspath(start_path)

    while True:
        file_path = os.path.join(current_path, "launchflow.yaml")
        if os.path.isfile(file_path):
            return file_path

        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            break

        current_path = parent_path

    return None


launchflow_config = None


def load_launchflow_dot_yaml():
    global launchflow_config
    if launchflow_config is None:
        launchflow_config = LaunchFlowDotYaml.load_from_cwd()
    return launchflow_config
