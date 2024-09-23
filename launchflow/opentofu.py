from dataclasses import make_dataclass
from typing import Any, Dict, Optional

from launchflow.config import config
from launchflow.models.flow_state import EnvironmentState
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.workflows.apply_resource_tofu.create_tofu_resource import (
    update_aws_tofu_resource_outputs,
    update_gcp_tofu_resource_outputs,
)
from launchflow.workflows.commands.tf_commands import TFApplyCommand
from launchflow.workflows.utils import run_tofu


class OpenTofuModule(Resource[Dict[str, Any]]):
    def __init__(self, name: str, module: str, **kwargs) -> None:
        super().__init__(name)
        self._module = module
        self._inputs = kwargs
        fields = [(key, type(value)) for key, value in kwargs.items()]

        # This is kind of hacky I feel like we should just allow the inputs
        # method to return a dictionary
        InputsClass = make_dataclass("InputsClass", fields, bases=(Inputs,))
        self._inputs = InputsClass(**kwargs)

    def inputs(self, environment_state: EnvironmentState):  # type: ignore
        return self._inputs

    def tofu_vars(self, environment_state: EnvironmentState) -> Dict[str, Any]:
        return self.execute_inputs(environment_state).to_dict()

    async def plan(self, output_file: str, launchflow_uri: LaunchFlowURI) -> None:
        pass

    async def apply(
        self,
        lock_id: str,
        environment: EnvironmentState,
        launchflow_uri: LaunchFlowURI,
        logs_file: str,
        plan_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        # TODO: pass in the plan file so we can apply with that
        state_prefix = launchflow_uri.tf_state_prefix(module=self.name)
        lf_state_url = launchflow_uri.launchflow_tofu_state_url(
            lock_id=lock_id, module=self.name
        )
        tf_apply_command = TFApplyCommand(
            tf_module_dir=self._module,
            backend=config.backend,  # type: ignore
            tf_state_prefix=state_prefix,
            tf_vars=self.tofu_vars(environment),
            logs_file=logs_file,
            launchflow_state_url=lf_state_url,
        )
        tf_outputs = await run_tofu(tf_apply_command)

        if environment.gcp_config is not None:
            await update_gcp_tofu_resource_outputs(
                artifact_bucket=environment.gcp_config.artifact_bucket,  # type: ignore
                resource_name=launchflow_uri.resource_name,  # type: ignore
                outputs=tf_outputs,
            )
        if environment.aws_config is not None:
            await update_aws_tofu_resource_outputs(
                artifact_bucket=environment.aws_config.artifact_bucket,  # type: ignore
                resource_name=launchflow_uri.resource_name,  # type: ignore
                outputs=tf_outputs,
            )
        return tf_outputs
