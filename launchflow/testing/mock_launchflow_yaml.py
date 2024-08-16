import dataclasses
import shutil
import tempfile
from typing import Any
from unittest import mock

import launchflow
from launchflow.backend import BackendOptions, LaunchFlowBackend, LocalBackend
from launchflow.config.launchflow_yaml import LaunchFlowDotYaml


@dataclasses.dataclass
class LaunchFlowYamlMock:
    launchflow_yaml: LaunchFlowDotYaml
    # TODO: Find a better way to type this
    load_launchflow_yaml_mock: Any
    launchflow_project_mock: Any
    launchflow_environment_mock: Any
    temp_dir: str

    def start(self):
        self.load_launchflow_yaml_mock.start()
        self.launchflow_project_mock.start()
        self.launchflow_environment_mock.start()

    def stop(self):
        shutil.rmtree(self.temp_dir)
        self.launchflow_environment_mock.stop()
        self.launchflow_project_mock.stop()
        self.load_launchflow_yaml_mock.stop()


def mock_launchflow_yaml_local_backend():
    tempdir = tempfile.mkdtemp()
    backend = LocalBackend(path=tempdir)
    launchflow_yaml = LaunchFlowDotYaml(
        project="unittest",
        backend=backend,
        backend_options=BackendOptions(),
        default_environment="test",
        config_path=f"{tempdir}/launchflow.yaml",
    )
    load_launchflow_yaml_mock = mock.patch(
        "launchflow.config.launchflow_config.load_launchflow_dot_yaml",
        return_value=launchflow_yaml,
    )
    launchflow_project_mock = mock.patch(
        "launchflow.project", new=launchflow_yaml.project
    )
    launchflow_environment_mock = mock.patch(
        "launchflow.environment", new=launchflow_yaml.default_environment
    )
    return LaunchFlowYamlMock(
        launchflow_yaml,
        load_launchflow_yaml_mock,
        launchflow_project_mock,
        launchflow_environment_mock,
        tempdir,
    )


# TODO: Reconcile this with the local backend mock utility above
def mock_launchflow_yaml_remote_backend(account_id: str = "account_id"):
    tempdir = tempfile.mkdtemp()
    backend = LaunchFlowBackend(account_id=account_id)
    launchflow_yaml = LaunchFlowDotYaml(
        project="unittest",
        backend=backend,
        backend_options=BackendOptions(),
        default_environment="test",
        config_path=f"{tempdir}/launchflow.yaml",
    )
    load_launchflow_yaml_mock = mock.patch(
        "launchflow.config.launchflow_config.load_launchflow_dot_yaml",
        return_value=launchflow_yaml,
    )
    launchflow_project_mock = mock.patch(
        "launchflow.project", return_value=launchflow_yaml.project
    )
    launchflow_environment_mock = mock.patch(
        "launchflow.environment", return_value=launchflow_yaml.default_environment
    )
    launchflow.lf_config.env.api_key = "key"
    return LaunchFlowYamlMock(
        launchflow_yaml,
        load_launchflow_yaml_mock,
        launchflow_project_mock,
        launchflow_environment_mock,
        tempdir,
    )
