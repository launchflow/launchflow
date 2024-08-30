import logging
from typing import Optional

import beaupy  # type: ignore
import rich
import typer

from launchflow import exceptions
from launchflow.cli.constants import ENVIRONMENT_HELP
from launchflow.cli.utils import OutputFormat, json_to_yaml
from launchflow.cli.utyper import UTyper
from launchflow.config import config
from launchflow.flows.environments_flows import get_environment
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.utils import RESOURCE_PRODUCTS_TO_RESOURCES
from launchflow.resource import Resource

app = UTyper(help="Commands for viewing resources managed by LaunchFlow")


@app.command()
async def list(
    environment: Optional[str] = typer.Argument(None, help=ENVIRONMENT_HELP),
    output_format: OutputFormat = typer.Option(
        "default", "--format", "-f", help="Output format"
    ),
):
    """List all resources in a project/environment."""
    ps_manager = ProjectManager(
        backend=config.launchflow_yaml.backend, project_name=config.project
    )
    environment_name, _ = await get_environment(
        ps_manager,
        environment_name=environment,
        prompt_for_creation=False,
    )
    environment_manager = ps_manager.create_environment_manager(environment_name)
    resources = await environment_manager.list_resources()
    local_resources = await environment_manager.list_docker_resources()
    resources.update(local_resources)

    if output_format == OutputFormat.YAML:
        output_dict = {
            name: resource.model_dump(
                mode="json", exclude_defaults=True, exclude_none=True
            )
            for name, resource in resources.items()
        }
        print(json_to_yaml(output_dict))
    else:
        if not resources:
            print("No resources found.")
            return

        print("Resources:")
        for name, resource in resources.items():
            resource_cls = RESOURCE_PRODUCTS_TO_RESOURCES.get(
                resource.product, Resource
            )
            print(f"- {resource_cls.__name__}(name='{name}')")


@app.command()
async def unlock(
    environment: str = typer.Argument(..., help=ENVIRONMENT_HELP),
    resource: str = typer.Argument(..., help="The resource to unlock."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve environment force unlock."
    ),
):
    """Force unlock a resource."""
    ps_manager = ProjectManager(
        backend=config.launchflow_yaml.backend, project_name=config.project
    )
    environment_name, env = await get_environment(
        ps_manager,
        environment_name=environment,
        prompt_for_creation=False,
    )
    environment_manager = ps_manager.create_environment_manager(environment_name)
    resource_manager = environment_manager.create_resource_manager(resource)

    if not auto_approve:
        rich.print(
            f"[yellow]Are you sure you want to force unlock Resource '{resource}'? This can lead to data corruption or conflicts.[/yellow]"
        )
        # TODO: Link to docs that explain what force unlock does
        if not beaupy.confirm("Force unlock Resource?"):
            rich.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    try:
        await resource_manager.force_unlock_resource()
        rich.print(
            f"[green]Resource '{resource}' force unlocked in Environment '{environment_name}'.[/green]"
        )
    except exceptions.EntityNotLocked:
        rich.print(
            f"[yellow]Resource '{resource}' is not locked. Nothing to unlock.[/yellow]"
        )
        raise typer.Exit(1)
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
