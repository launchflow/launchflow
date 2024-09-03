import asyncio
import dataclasses
import importlib
import importlib.resources
import importlib.util
import json
import os
import shutil
from typing import Any, Dict, List, Optional, Union

import httpx

from launchflow import exceptions
from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend
from launchflow.config import config
from launchflow.dependencies import opentofu
from launchflow.logger import logger
from launchflow.utils import logging_output

_GCS_BACKEND_TEMPLATE = """
terraform {
  backend "gcs" {
  }
}
"""

_LOCAL_BACKEND_TEMPLATE = """
terraform {
  backend "local" {
  }
}
"""


def parse_value(value, type_info):
    if value is None:
        return None
    if type_info == "string":
        return str(value)
    elif type_info == "number":
        return float(value) if "." in str(value) else int(value)
    elif type_info == "bool":
        return bool(value)
    elif isinstance(type_info, list):
        type_category = type_info[0]
        if type_category == "list":
            element_type = type_info[1][1]
            return [parse_value(elem, element_type) for elem in value]
        elif type_category == "map":
            value_type = type_info[1]
            return {key: parse_value(val, value_type) for key, val in value.items()}
        elif type_category == "set":
            element_type = type_info[1][1]
            return {parse_value(elem, element_type) for elem in value}
        elif type_category == "object":
            properties = type_info[1]
            return {key: parse_value(value[key], properties[key]) for key in properties}
    return value


def parse_tf_outputs(tf_outputs_json: dict) -> Dict[str, Any]:
    parsed_outputs = {}
    for key, output in tf_outputs_json.items():
        value = output["value"]
        type_info = output["type"]
        parsed_value = parse_value(value, type_info)
        parsed_outputs[key] = parsed_value
    return parsed_outputs


@dataclasses.dataclass
class TFCommand:
    # The path of the tf module relative to launchflow/workflows/tf
    tf_module_dir: str
    backend: Union[LocalBackend, LaunchFlowBackend, GCSBackend]
    # If empty will use the current working directory
    tf_state_prefix: str
    # The file to write logs to, if not provided, logs will be written to stdout
    logs_file: Optional[str]
    # The backend url for launchflow tofu state
    launchflow_state_url: Optional[str]

    def initialize_working_dir(self, working_dir: str):
        # TODO(oss): maybe we should verify there is no existing backend definition
        # I think tf will fail there is, but might nice to have a better error message
        backed_config_path = os.path.join(working_dir, "backend.tf")
        with open(backed_config_path, "w") as f:
            if isinstance(self.backend, (LocalBackend, LaunchFlowBackend)):
                f.write(_LOCAL_BACKEND_TEMPLATE)
            elif isinstance(self.backend, GCSBackend):
                f.write(_GCS_BACKEND_TEMPLATE)
            else:
                raise ValueError(f"Unsupported backend type: {self.backend}")

        if isinstance(self.backend, LaunchFlowBackend):
            # Download state from launchflow and write it in the temporary directory
            with httpx.Client() as client:
                response = client.get(
                    f"{self.backend.lf_cloud_url}/v1/projects/{self.launchflow_state_url}",
                    headers={"Authorization": f"Bearer {config.get_access_token()}"},
                )
                if response.status_code == 200:
                    state = response.json()
                    tf_state_path = os.path.join(working_dir, "default.tfstate")
                    with open(tf_state_path, "w") as f:
                        json.dump(state, f)
                elif response.status_code != 404:
                    raise ValueError("Failed to load tofu state, please try again.")

        with importlib.resources.path(
            "launchflow.workflows.tf", "__init__.py"
        ) as init_path:
            module_path = init_path.parent / self.tf_module_dir

            for file in module_path.iterdir():
                shutil.copy(file, working_dir)

    def tf_init_command(self) -> str:
        if isinstance(self.backend, LocalBackend):
            path = os.path.join(
                self.tf_state_prefix,
                "default.tfstate",
            )
            command_lines = [
                f"{opentofu.TOFU_PATH} init -reconfigure",
                f'-backend-config "path={os.path.abspath(path)}"',
            ]
        elif isinstance(self.backend, GCSBackend):
            command_lines = [
                f"{opentofu.TOFU_PATH} init -reconfigure",
                f'-backend-config "bucket={self.backend.bucket}"',
                f'-backend-config "prefix={self.tf_state_prefix}"',
            ]
        elif isinstance(self.backend, LaunchFlowBackend):
            command_lines = [
                f"{opentofu.TOFU_PATH} init -reconfigure",
                f'-backend-config "path={self.tf_state_prefix}"',
            ]
        else:
            raise ValueError(f"Unsupported backend type: {self.backend}")
        return " ".join(command_lines)

    async def run(self, working_dir: str):
        try:
            return await self._run(working_dir)
        finally:
            tf_state_path = os.path.join(working_dir, self.tf_state_prefix)

            if isinstance(self.backend, LaunchFlowBackend) and os.path.exists(
                tf_state_path
            ):
                # Upload the state to launchflow
                with open(tf_state_path, "r") as f:
                    state = json.load(f)
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        f"{self.backend.lf_cloud_url}/v1/projects/{self.launchflow_state_url}",
                        json=state,
                        headers={
                            "Authorization": f"Bearer {config.get_access_token()}"
                        },
                    )
                    if response.status_code != 200:
                        raise ValueError(
                            "Failed to upload tofu state, please try again."
                        )

    async def _run(self, working_dir: str):
        raise NotImplementedError("_run method not implemented")

    def _var_flags(self):
        var_flags = []
        for key, value in self.tf_vars.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            if isinstance(value, bool):
                value = str(value).lower()
            var_flags.extend(["-var", f"{key}={value}"])
        return var_flags


@dataclasses.dataclass
class TFDestroyCommand(TFCommand):
    tf_vars: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def tf_destroy_command(self) -> List[str]:
        return [
            f"{opentofu.TOFU_PATH}",
            "destroy",
            "-auto-approve",
            "-input=false",
            *self._var_flags(),
        ]

    async def _run(self, working_dir: str):
        with logging_output(self.logs_file) as f:
            self.initialize_working_dir(working_dir)

            # Run tofu init
            logger.info(f"Running tofu init command: {self.tf_init_command()}")
            proc = await asyncio.create_subprocess_shell(
                self.tf_init_command(),
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            status_code = await proc.wait()
            if status_code != 0:
                raise exceptions.TofuInitFailure()

            # Run tofu destroy
            logger.info(f"Running tofu destroy command: {self.tf_destroy_command()}")
            proc = await asyncio.create_subprocess_exec(
                *self.tf_destroy_command(),
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            await proc.communicate()

            if proc.returncode != 0:
                raise exceptions.TofuDestroyFailure()

            return True


@dataclasses.dataclass
class TFApplyCommand(TFCommand):
    tf_vars: Dict[str, Any]

    def tf_apply_command(self) -> List[str]:
        return [
            f"{opentofu.TOFU_PATH}",
            "apply",
            "-auto-approve",
            "-input=false",
            *self._var_flags(),
        ]

    async def _run(self, working_dir: str) -> Dict[str, Any]:
        self.initialize_working_dir(working_dir)

        with logging_output(self.logs_file) as f:
            # Run tofu init
            logger.info(f"Running tofu init command: {self.tf_init_command()}")
            proc = await asyncio.create_subprocess_shell(
                self.tf_init_command(),
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            status_code = await proc.wait()
            if status_code != 0:
                raise exceptions.TofuInitFailure()

            # Run tofu apply
            logger.info(f"Running tofu apply command: {self.tf_apply_command()}")
            proc = await asyncio.create_subprocess_exec(
                *self.tf_apply_command(),
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            tf_logs, _ = await proc.communicate()
            if proc.returncode != 0:
                raise exceptions.TofuApplyFailure()

            # Run tofu output
            tofu_output_command = f"{opentofu.TOFU_PATH} output --json"
            logger.info(f"Running tofu output command: {tofu_output_command}")
            proc = await asyncio.create_subprocess_shell(
                tofu_output_command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                raise exceptions.TofuOutputFailure()
            tf_outputs_json = json.loads(stdout)
            return parse_tf_outputs(tf_outputs_json)


@dataclasses.dataclass
class TFImportCommand(TFApplyCommand):
    resource: str
    resource_id: str
    drop_logs: bool

    def tf_import_command(self, resource: str, resource_id: str) -> List[str]:
        return [
            f"{opentofu.TOFU_PATH}",
            "import",
            "-input=false",
            *self._var_flags(),
            resource,
            resource_id,
        ]

    async def _run(self, working_dir: str):
        self.initialize_working_dir(working_dir)

        with logging_output(self.logs_file, drop_logs=self.drop_logs) as f:
            # Run tofu init
            logger.info(f"Running tofu init command: {self.tf_init_command()}")
            proc = await asyncio.create_subprocess_shell(
                self.tf_init_command(),
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            status_code = await proc.wait()
            if status_code != 0:
                raise exceptions.TofuInitFailure()

            # Run tofu import
            command = self.tf_import_command(self.resource, self.resource_id)
            logger.info(f"Running tofu import command: {command}")
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                # Stops the child process from receiving signals sent to the parent
                preexec_fn=os.setpgrp,
                stdout=f,
                stderr=f,
            )
            status_code = await proc.wait()
            if status_code != 0:
                raise exceptions.TofuImportFailure()
