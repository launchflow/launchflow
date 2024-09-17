import dataclasses
import os
from typing import List, Optional

from typing_extensions import Literal

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class CodeBuildProjectOutputs(Outputs):
    project_name: str


@dataclasses.dataclass
class Cache(Inputs):
    type: Literal["NO_CACHE", "LOCAL", "S3"]
    location: Optional[str] = None
    modes: Optional[
        List[
            Literal[
                "LOCAL_SOURCE_CACHE", "LOCAL_DOCKER_LAYER_CACHE", "LOCAL_CUSTOM_CACHE"
            ]
        ]
    ] = None

    def __post_init__(self):
        if self.type == "S3" and not self.location:
            raise ValueError("location must be provided when type is S3")


@dataclasses.dataclass
class EnvironmentVariable:
    name: str
    value: str


@dataclasses.dataclass
class Environment(Inputs):
    compute_type: Literal[
        "BUILD_GENERAL1_SMALL",
        "BUILD_GENERAL1_MEDIUM",
        "BUILD_GENERAL1_LARGE",
        "BUILD_GENERAL1_2XLARGE",
        "BUILD_LAMBDA_1GB",
        "BUILD_LAMBDA_2GB",
        "BUILD_LAMBDA_4GB",
        "BUILD_LAMBDA_8GB",
        "BUILD_LAMBDA_10GB",
    ]
    image: str
    type: Literal[
        "LINUX_CONTAINER",
        "LINUX_GPU_CONTAINER",
        "WINDOWS_CONTAINER",
        "ARM_CONTAINER",
        "LINUX_LAMBDA_CONTAINER",
        "ARM_LAMBDA_CONTAINER",
    ]
    image_pull_credentials_type: Literal["CODEBUILD", "SERVICE_ROLE"] = "CODEBUILD"
    environment_variables: List[EnvironmentVariable] = dataclasses.field(
        default_factory=list
    )
    privileged_mode: bool = False

    def __post_init__(self):
        if (
            self.type != "LINUX_CONTAINER"
            and self.compute_type == "BUILD_GENERAL1_SMALL"
        ):
            raise ValueError(
                "compute_type BUILD_GENERAL1_SMALL is not supported for non-LINUX_CONTAINER environments"
            )
        if (
            self.type == "LINUX_GPU_CONTAINER"
            and self.compute_type != "BUILD_GENERAL1_LARGE"
        ):
            raise ValueError(
                "compute_type must be BUILD_GENERAL1_LARGE for LINUX_GPU_CONTAINER environments"
            )
        if "LAMBDA" in self.type and "LAMBDA" not in self.compute_type:
            raise ValueError(
                "compute_type must be a LAMBDA type for LAMBDA environments"
            )


@dataclasses.dataclass
class CloudWatchLogsConfig(Inputs):
    status: Literal["ENABLED", "DISABLED"]
    group_name: Optional[str] = None
    stream_name: Optional[str] = None


@dataclasses.dataclass
class S3LogsConfig(Inputs):
    status: Literal["ENABLED", "DISABLED"]
    location: Optional[str] = None

    def __post_init__(self):
        if self.status == "ENABLED" and not self.location:
            raise ValueError("location must be provided when status is ENABLED")


@dataclasses.dataclass
class LogsConfig(Inputs):
    cloud_watch_logs: Optional[CloudWatchLogsConfig] = None
    s3_logs: Optional[S3LogsConfig] = None


@dataclasses.dataclass
class Source(Inputs):
    type: Literal["NO_SOURCE", "S3"]
    location: Optional[str] = None
    buildspec_path: Optional[str] = None

    def __post_init__(self):
        if self.buildspec_path is None and self.type == "NO_SOURCE":
            raise ValueError("buildspec_path cannot be None when type is NO_SOURCE")
        if self.buildspec_path is not None and not os.path.exists(self.buildspec_path):
            raise ValueError(f"buildspec_path {self.buildspec_path} does not exist")
        if self.location is None and self.type == "S3":
            raise ValueError("location cannot be None when type is S3")
        if self.buildspec_path is not None:
            self.buildspec_path = os.path.abspath(self.buildspec_path)


@dataclasses.dataclass
class CodeBuildProjectInputs(ResourceInputs):
    build_timeout_minutes: int
    environment: Environment
    build_source: Source
    cache: Optional[Cache]
    logs_config: Optional[LogsConfig]


# TODO: improve this docstring
class CodeBuildProject(AWSResource[CodeBuildProjectOutputs]):
    """A resource for creating a CodeBuild project.

    ### Example Usage
    ```python
    import launchflow as lf

    codebuild_environment = lf.aws.codebuild_project.Environment(...)
    codebuild_source = lf.aws.codebuild_project.Source(...)
    codebuild_project = lf.aws.CodeBuildProject("my-codebuild-project", environment=)
    ```
    """

    product = ResourceProduct.AWS_CODEBUILD_PROJECT.value

    def __init__(
        self,
        name: str,
        *,
        environment: Environment,
        build_source: Source,
        logs_config: Optional[LogsConfig] = None,
        cache: Optional[Cache] = None,
        build_timeout_minutes: int = 30,
    ) -> None:
        """Create a new CodeBuildProject resource.

        **Args:**
        - `name (str)`: The name of the CodeBuildProject resource. This must be globally unique.
        - `environment (Environment)`: The CodeBuild project environment to use.
        - `build_source (Source)`: The CodeBuild project source to use.
        - `logs_config (Optional[LogsConfig])`: The logs configuration for the CodeBuild project. Defaults to None.
        - `cache (Optional[Cache])`: The cache configuration for the CodeBuild project. Defaults to None.
        - `build_timeout_minutes: int`: The build timeout for the CodeBuild project. Default to 30 minutes.
        """
        # TODO: figure out replace args
        super().__init__(name=name, resource_id=f"{name}-{lf.project}-{lf.environment}")
        self.environment = environment
        self.build_source = build_source
        self.logs_config = logs_config
        self.cache = cache
        self.build_timeout_minutes = build_timeout_minutes

    def inputs(self, environment_state: EnvironmentState) -> CodeBuildProjectInputs:
        return CodeBuildProjectInputs(
            resource_id=self.resource_id,
            build_timeout_minutes=self.build_timeout_minutes,
            environment=self.environment,
            build_source=self.build_source,
            cache=self.cache,
            logs_config=self.logs_config,
        )
