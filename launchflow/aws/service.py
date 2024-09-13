from launchflow.models.enums import CloudProvider
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import (
    BuildOutputs,
    ReleaseInputs,
    ReleaseOutputs,
    Service,
    ServiceOutputs,
)


class AWSService(Service[ServiceOutputs]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS

    async def build(
        self,
        *,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_local: bool,
    ) -> BuildOutputs:
        raise NotImplementedError

    async def promote(
        self,
        *,
        from_aws_environment_config: AWSEnvironmentConfig,
        to_aws_environment_config: AWSEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_local: bool,
    ) -> BuildOutputs:
        raise NotImplementedError

    async def release(
        self,
        *,
        release_inputs: ReleaseInputs,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
    ) -> ReleaseOutputs:
        raise NotImplementedError
