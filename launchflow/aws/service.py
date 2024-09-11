from typing import Tuple

from launchflow.models.enums import CloudProvider
from launchflow.models.flow_state import AWSEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import Service, ServiceOutputs


class AWSService(Service[ServiceOutputs]):
    def cloud_provider(self) -> CloudProvider:
        return CloudProvider.AWS

    # NOTE: The tuple returned by build() is passed to release() as *args
    async def build(
        self,
        *,
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_local: bool,
    ) -> Tuple:  # TODO: Make this a dataclass
        raise NotImplementedError

    # NOTE: The tuple returned by promote() is passed to release() as *args
    async def promote(
        self,
        *,
        from_aws_environment_config: AWSEnvironmentConfig,
        to_aws_environment_config: AWSEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        promote_local: bool,
    ) -> Tuple:  # TODO: Make this a dataclass
        raise NotImplementedError

    # NOTE: The str returned by release() is the service url
    async def release(
        self,
        *args,  # TODO: Make this a dataclass
        aws_environment_config: AWSEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
    ) -> str:
        raise NotImplementedError
