from typing import Optional

import beaupy  # type: ignore
import httpx
import rich
import typer

from launchflow import exceptions
from launchflow.cli.utils import print_response
from launchflow.cli.utyper import UTyper
from launchflow.clients import async_launchflow_client_ctx
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.config import config
from launchflow.exceptions import LaunchFlowException
from launchflow.flows.project_flows import create_project
from launchflow.managers.project_manager import ProjectManager
from launchflow.validation import validate_project_name

app = UTyper(help="Interact with your LaunchFlow projects.")


def _check_lf_cloud_credentials():
    if config.credentials is None:
        rich.print("[red]No LaunchFlow Cloud credentials found.[/red]")
        rich.print("Please run `lf login` to login or sign up for an account.\n")
        rich.print(
            "[yellow]NOTE: This command only supports LaunchFlow Cloud backends.[/yellow]"
        )
        raise typer.Exit(1)


@app.command()
async def list():
    """Lists all current projects in your account."""
    _check_lf_cloud_credentials()

    base_url = config.get_launchflow_cloud_url()
    account_id = config.get_account_id()
    async with httpx.AsyncClient(timeout=60) as client:
        proj_client = ProjectsAsyncClient(
            http_client=client, launchflow_account_id=account_id, base_url=base_url
        )
        projects = await proj_client.list()
    print_response(
        "Projects",
        {
            "projects": [
                projects.model_dump(exclude_defaults=True) for projects in projects
            ]
        },
    )


@app.command()
async def create(
    project: Optional[str] = typer.Argument(None, help="The project name."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve project creation."
    ),
):
    """Create a new project in your account."""
    _check_lf_cloud_credentials()

    # TODO: Make this a separate utility and update other CRUD commands to use it
    if project is None:
        if auto_approve:
            typer.echo(
                "Project name is required for auto approval. (i.e. `lf projects create my-project -y`)"
            )
            raise typer.Exit(1)
        project = beaupy.prompt("What would you like to name your LaunchFlow project?")
        while True:
            try:
                validate_project_name(project)  # type: ignore
                break
            except ValueError as e:
                reason = str(e)
                rich.print(f"[red]{reason}[/red]")
                project = beaupy.prompt("Please enter a new project name.")

    else:
        validate_project_name(project)

    lf_project = None
    async with httpx.AsyncClient(timeout=60) as client:
        proj_client = ProjectsAsyncClient(
            http_client=client,
            launchflow_account_id=config.get_account_id(),
            base_url=config.get_launchflow_cloud_url(),
        )
        try:
            lf_project = await create_project(
                client=proj_client,
                project_name=project,  # type: ignore
                account_id=config.get_account_id(),
                prompt=not auto_approve,
            )
        except LaunchFlowException:
            raise typer.Exit(1)

    if lf_project is not None:
        print_response("Project", lf_project.model_dump(exclude_defaults=True))


@app.command()
async def delete(
    name: str = typer.Argument(..., help="The project name."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve project deletion."
    ),
):
    """Delete a project."""
    _check_lf_cloud_credentials()

    base_url = config.get_launchflow_cloud_url()

    async with async_launchflow_client_ctx(
        config.get_account_id(),
        base_url=base_url,
    ) as client:
        try:
            await client.projects.get(name)
        except exceptions.ProjectNotFound:
            rich.print(f"[red]Project '{name}' not found.[/red]")
            raise typer.Exit(1)

        if not auto_approve:
            user_confirmation = beaupy.confirm(
                f"Would you like to delete the project `{name}`?",
                default_is_yes=True,
            )
            if not user_confirmation:
                rich.print("[red]✗[/red] Project deletion canceled.")
                typer.Exit(1)

        backend = config.launchflow_yaml.backend
        ps_manager = ProjectManager(backend=backend, project_name=name)
        environments = await ps_manager.list_environments()
        if environments:
            raise exceptions.ProjectNotEmpty(project_name=name)

        try:
            await client.projects.delete(name)
            rich.print("[green]✓[/green] Project deleted.")
        except Exception as e:
            typer.echo(e)
            raise typer.Exit(1)
