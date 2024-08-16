import os
from dataclasses import dataclass
from typing import Optional


def get_boolean_variable(name: str, default_value: Optional[bool] = None) -> bool:
    true_ = ("true", "1")
    false_ = ("false", "0")
    value: Optional[str] = os.getenv(name, None)
    if value is None:
        if default_value is None:
            raise ValueError(f"Required variable `{name}` not set!")
        else:
            value = str(default_value)
    if value.lower() not in true_ + false_:
        raise ValueError(f"Invalid value `{value}` for variable `{name}`")
    return value.lower() in true_


@dataclass
class LaunchFlowEnvVars:
    project: Optional[str] = None
    cloud_provider: Optional[str] = None
    environment: Optional[str] = None
    api_key: Optional[str] = None
    artifact_bucket: Optional[str] = None
    outputs_path: Optional[str] = None
    deployment_id: Optional[str] = None
    run_cache: Optional[str] = None

    @classmethod
    def load_from_env(cls):
        """
        Loads the object's properties from environment variables.

        Returns:
            An instance of LaunchFlowDotEnv with properties populated from environment variables.
        """
        project = os.getenv("LAUNCHFLOW_PROJECT", None)
        cloud_provider = os.getenv("LAUNCHFLOW_CLOUD_PROVIDER", None)
        environment = os.getenv("LAUNCHFLOW_ENVIRONMENT", None)
        api_key = os.getenv("LAUNCHFLOW_API_KEY", None)
        artifact_bucket = os.getenv("LAUNCHFLOW_ARTIFACT_BUCKET", None)
        outputs_path = os.getenv("LAUNCHFLOW_OUTPUTS_PATH", None)
        # TODO: Maybe explore using this field to determine if new versions of a service
        # were deployed (assuming we provide some service discovery mechanism)
        deployment_id = os.getenv("LAUNCHFLOW_DEPLOYMENT_ID", None)
        run_cache = os.getenv("LAUNCHFLOW_RUN_CACHE", None)

        return cls(
            project=project,
            cloud_provider=cloud_provider,
            environment=environment,
            api_key=api_key,
            artifact_bucket=artifact_bucket,
            outputs_path=outputs_path,
            deployment_id=deployment_id,
            run_cache=run_cache,
        )


launchflow_env_vars = None


# NOTE: We use a global variable so its only loaded once
def load_launchflow_env():
    global launchflow_env_vars
    if launchflow_env_vars is None:
        launchflow_env_vars = LaunchFlowEnvVars.load_from_env()
    return launchflow_env_vars
