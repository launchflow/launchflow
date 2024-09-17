from typing import Optional

import beaupy  # type: ignore
import rich
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.clients.response_schemas import ProjectResponse
from launchflow.exceptions import LaunchFlowRequestFailure


async def get_project(
    client: ProjectsAsyncClient,
    account_id: str,
    project_name: Optional[str],
    prompt_for_creation: bool = False,
    custom_selection_prompt: Optional[str] = None,
    console: rich.console.Console = rich.console.Console(),
) -> ProjectResponse:
    if project_name is None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Fetching projects...", total=None)
            projects = await client.list()
            progress.remove_task(task)

        project_names = [p.name for p in projects]
        if prompt_for_creation:
            project_names.append("[i yellow]Create new project[/i yellow]")
        if custom_selection_prompt is not None:
            console.print(custom_selection_prompt)
        else:
            console.print("Select the project to use:")
        selected_project = beaupy.select(project_names, return_index=True, strict=True)
        if selected_project is None:
            console.print("[pink1]No project selected.[/pink1]")
            console.print("\n[red]✗ Project selection canceled.[/red]")
            raise typer.Exit(1)
        if prompt_for_creation and selected_project == len(project_names) - 1:
            if project_name is None:
                project_name = beaupy.prompt("Enter the project name:")
            while project_name in project_names:
                project_name = beaupy.prompt(
                    f"`{project_name}` is already taken. Enter a different name:"
                )
            if project_name is None:
                typer.echo("Project creation canceled.")
                raise typer.Exit(1)
            console.print(f"[pink1]>[/pink1] {project_name}")
            project = await create_project(client, project_name, account_id)
        else:
            project = projects[selected_project]
            console.print(f"[pink1]>[/pink1] {project.name}")
        return project
    try:
        # Fetch the project to ensure it exists
        project = await client.get(project_name)
    except LaunchFlowRequestFailure as e:
        if e.status_code == 404 and prompt_for_creation:
            answer = beaupy.confirm(
                f"Project `{project_name}` does not exist yet. Would you like to create it?"
            )
            if answer:
                # TODO: this will just use their default account. Should maybe ask them.
                # But maybe that should be in the create project flow?
                project = await create_project(client, project_name, account_id)
            else:
                raise e
        else:
            raise e
    return project


async def create_project(
    client: ProjectsAsyncClient,
    project_name: str,
    account_id: str,
    prompt: bool = True,
):
    if prompt:
        user_confirmation = beaupy.confirm(
            f"Would you like to create a new project `{project_name}` in your LaunchFlow account `{account_id}`?",
            default_is_yes=True,
        )
        if not user_confirmation:
            rich.print("[red]✗[/red] Project creation canceled.")
            return

    project = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Creating LaunchFlow Project...", total=None)
        try:
            project = await client.create(project_name)
        except Exception as e:
            progress.console.print("[red]✗[/red] Failed to create project.")
            progress.console.print(
                "    └── NOTE: You can re-run this command to retry creating the project."
            )
            progress.console.print(f"    └── {str(e)}")
            raise e
        finally:
            progress.update(task, advance=1)
            progress.remove_task(task)
    progress.console.print("[green]✓[/green] Project created successfully.")
    return project
