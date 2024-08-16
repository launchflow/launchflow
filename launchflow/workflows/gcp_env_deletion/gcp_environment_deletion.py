from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from launchflow import exceptions
from launchflow.workflows.gcp_env_deletion.schemas import GCPEnvironmentDeletionInputs


async def delete_gcp_environment(inputs: GCPEnvironmentDeletionInputs):
    if inputs.environment_state.gcp_config is None:
        return
    try:
        from google.api_core.exceptions import FailedPrecondition
        from google.cloud import resourcemanager_v3
    except ImportError:
        raise exceptions.MissingGCPDependency()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn("["),
        TimeElapsedColumn(),
        TextColumn("]"),
    ) as progress:
        # Only delete the project if we're detaching
        delete_task = progress.add_task(
            f"Deleting GCP project {inputs.environment_state.gcp_config.project_id}...",
            total=None,
        )
        projects_client = resourcemanager_v3.ProjectsAsyncClient()
        try:
            operation = await projects_client.delete_project(
                name="projects/{}".format(
                    inputs.environment_state.gcp_config.project_id
                )
            )
            await operation.result()
        except FailedPrecondition as e:
            # This case happens when the project is already pending deletion
            if e.message != "Project not active":
                raise e
        progress.console.print(
            f"[green]✓ GCP Project: `{inputs.environment_state.gcp_config.project_id}` successfully deleted[/green]"
        )
        progress.remove_task(delete_task)
