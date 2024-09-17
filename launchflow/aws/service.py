from typing import IO

from launchflow import exceptions
from launchflow.models.enums import CloudProvider
from launchflow.models.flow_state import AWSEnvironmentConfig, EnvironmentState
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import R, Service


class AWSService(Service[R]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS

    # TODO: Consider making this a property on the EnvironmentState
    def _aws_environment_config(
        self, environment_state: EnvironmentState, environment_name: str
    ) -> AWSEnvironmentConfig:
        aws_environment_config = environment_state.aws_config
        if aws_environment_config is None:
            raise exceptions.AWSConfigNotFound(environment_name=environment_name)
        return aws_environment_config

    async def build(
        self,
        *,
        environment_state: EnvironmentState,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> R:
        aws_environment_config = self._aws_environment_config(
            environment_state, launchflow_uri.environment_name
        )
        return await self._build(
            aws_environment_config=aws_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            build_log_file=build_log_file,
            build_local=build_local,
        )

    async def _build(
        self,
        *,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> R:
        raise NotImplementedError

    async def promote(
        self,
        *,
        from_environment_state: EnvironmentState,
        to_environment_state: EnvironmentState,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,
        promote_local: bool,
    ) -> R:
        from_aws_environment_config = self._aws_environment_config(
            from_environment_state,
            from_launchflow_uri.environment_name,
        )
        to_aws_environment_config = self._aws_environment_config(
            to_environment_state, to_launchflow_uri.environment_name
        )
        return await self._promote(
            from_aws_environment_config=from_aws_environment_config,
            to_aws_environment_config=to_aws_environment_config,
            from_launchflow_uri=from_launchflow_uri,
            to_launchflow_uri=to_launchflow_uri,
            from_deployment_id=from_deployment_id,
            to_deployment_id=to_deployment_id,
            promote_log_file=promote_log_file,
            promote_local=promote_local,
        )

    async def _promote(
        self,
        *,
        from_aws_environment_config: AWSEnvironmentConfig,
        to_aws_environment_config: AWSEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,
        promote_local: bool,
    ) -> R:
        raise NotImplementedError

    async def release(
        self,
        *,
        release_inputs: R,
        environment_state: EnvironmentState,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ) -> None:
        aws_environment_config = self._aws_environment_config(
            environment_state, launchflow_uri.environment_name
        )
        return await self._release(
            release_inputs=release_inputs,
            aws_environment_config=aws_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            release_log_file=release_log_file,
        )

    async def _release(
        self,
        *,
        release_inputs: R,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        raise NotImplementedError
