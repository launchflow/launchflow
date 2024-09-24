from typing import IO

from launchflow import exceptions
from launchflow.models.enums import CloudProvider
from launchflow.models.flow_state import EnvironmentState, GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import R, Service


class GCPService(Service[R]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.GCP

    # TODO: Consider making this a property on the EnvironmentState
    def _gcp_environment_config(
        self, environment_state: EnvironmentState, environment_name: str
    ) -> GCPEnvironmentConfig:
        gcp_environment_config = environment_state.gcp_config
        if gcp_environment_config is None:
            raise exceptions.GCPConfigNotFound(environment_name=environment_name)
        return gcp_environment_config

    async def build(
        self,
        *,
        environment_state: EnvironmentState,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> R:
        gcp_environment_config = self._gcp_environment_config(
            environment_state, launchflow_uri.environment_name
        )
        return await self._build(
            gcp_environment_config=gcp_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            build_log_file=build_log_file,
            build_local=build_local,
        )

    async def _build(
        self,
        *,
        gcp_environment_config: GCPEnvironmentConfig,
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
        from_gcp_environment_config = self._gcp_environment_config(
            from_environment_state,
            from_launchflow_uri.environment_name,
        )
        to_gcp_environment_config = self._gcp_environment_config(
            to_environment_state, to_launchflow_uri.environment_name
        )
        return await self._promote(
            from_gcp_environment_config=from_gcp_environment_config,
            to_gcp_environment_config=to_gcp_environment_config,
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
        from_gcp_environment_config: GCPEnvironmentConfig,
        to_gcp_environment_config: GCPEnvironmentConfig,
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
        gcp_environment_config = self._gcp_environment_config(
            environment_state, launchflow_uri.environment_name
        )
        return await self._release(
            release_inputs=release_inputs,
            gcp_environment_config=gcp_environment_config,
            launchflow_uri=launchflow_uri,
            deployment_id=deployment_id,
            release_log_file=release_log_file,
        )

    async def _release(
        self,
        *,
        release_inputs: R,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        raise NotImplementedError
