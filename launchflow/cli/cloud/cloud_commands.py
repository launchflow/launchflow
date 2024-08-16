from typing import Optional, Union

import rich
import typer

import launchflow
from launchflow.aws.launchflow_cloud_releaser import (
    LaunchFlowCloudReleaser as AWSReleaser,
)
from launchflow.backend import LaunchFlowBackend
from launchflow.cli.utyper import UTyper
from launchflow.config import config
from launchflow.flows.create_flows import create
from launchflow.flows.environments_flows import get_environment
from launchflow.gcp.launchflow_cloud_releaser import (
    LaunchFlowCloudReleaser as GCPReleaser,
)
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.enums import EnvironmentStatus

app = UTyper(help="Commands for interacting with LaunchFlow Cloud.")


@app.command()
async def connect(
    environment: Optional[str] = typer.Argument(
        None, help="The environment to connect."
    ),
):
    """Connect an environment to LaunchFlow.

    For GCP this will create a service account that will be able to deploy your services, and allow LaunchFlow Cloud to use the service account to trigger deployments.
    """

    if not isinstance(config.launchflow_yaml.backend, LaunchFlowBackend):
        typer.echo(
            f"Unsupported backend: {type(config.launchflow_yaml.backend)}. This command only supports LaunchFlow Cloud backends."
        )
        raise typer.Exit(1)

    if environment is None:
        pm = ProjectManager(
            project_name=config.project, backend=config.launchflow_yaml.backend
        )
        environment, env = await get_environment(pm, prompt_for_creation=False)
    else:
        manager = EnvironmentManager(
            project_name=config.launchflow_yaml.project,
            environment_name=environment,
            backend=config.launchflow_yaml.backend,
        )

        env = await manager.load_environment()

    if env.status != EnvironmentStatus.READY:
        typer.echo(
            f"Environment {environment} is not ready. Please ensure the enviroment is ready before connecting to LaunchFlow Cloud."
        )
        raise typer.Exit(1)

    rich.print("\nConnecting environment to LaunchFlow Cloud...")
    launchflow.environment = environment
    if env.gcp_config is not None:
        resource: Union[GCPReleaser, AWSReleaser] = GCPReleaser()
        create_results = await create(resource, environment=environment, prompt=False)  # type: ignore
    elif env.aws_config is not None:
        resource = AWSReleaser()
        create_results = await create(resource, environment=environment, prompt=False)  # type: ignore
    else:
        typer.echo(
            "LaunchFlow cloud only support connecting GCP and AWS environments at this time."
        )
        raise typer.Exit(1)
    if not create_results.success:
        raise typer.Exit(1)
    await resource.connect_to_launchflow()
