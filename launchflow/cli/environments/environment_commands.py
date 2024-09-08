import logging
from typing import Any, Dict, Optional

import beaupy  # type: ignore
import rich
import typer

from launchflow import exceptions
from launchflow.backend import LaunchFlowBackend
from launchflow.cli.utils import OutputFormat, json_to_yaml, print_response
from launchflow.cli.utyper import UTyper
from launchflow.config import config
from launchflow.flows.environments_flows import (
    create_environment,
    delete_environment,
    get_environment,
)
from launchflow.logger import logger
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.enums import CloudProvider, EnvironmentType
from launchflow.models.utils import (
    RESOURCE_PRODUCTS_TO_RESOURCES,
    SERVICE_PRODUCTS_TO_SERVICES,
)
from launchflow.validation import validate_environment_name

app = UTyper(help="Interact with your LaunchFlow environments.")


@app.command()
async def create(
    name: Optional[str] = typer.Argument(None, help="The environment name."),
    env_type: Optional[EnvironmentType] = typer.Option(
        None, help="The environment type (`development` or `production`)."
    ),
    cloud_provider: Optional[CloudProvider] = typer.Option(
        None, help="The cloud provider."
    ),
    # GCP cloud provider options, this are used if you are importing an existing setup
    gcp_project_id: Optional[str] = typer.Option(
        None, help="The GCP project ID to import."
    ),
    gcs_artifact_bucket: Optional[str] = typer.Option(
        None, help="The GCS bucket to import.", hidden=True
    ),
    gcp_organization_name: Optional[str] = typer.Option(
        None,
        help="The GCP organization name (organization/XXXXXX) to place newly create GCP projects in. If not provided you will be prompted to select an organization.",
    ),
    gcp_service_account_email: Optional[str] = typer.Option(
        None, help="The GCP service account email to import for the environment."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve environment creation."
    ),
):
    """Create a new environment in the current project."""
    if (
        gcp_project_id
        or gcs_artifact_bucket
        or gcp_service_account_email
        or gcp_organization_name
    ):
        if cloud_provider is not None and cloud_provider != CloudProvider.GCP:
            rich.print(
                "[red]Error: GCP options can only be used with the GCP cloud provider. Add the `--cloud-provider=gcp` flag and try again.[/red]"
            )
            raise typer.Exit(1)
        cloud_provider = CloudProvider.GCP

    if name is None:
        if auto_approve:
            typer.echo(
                "Environment name is required when using the --auto-approve | -y flag."
            )
            raise typer.Exit(1)

        name = beaupy.prompt("What would you like to name your Environment?")
        while True:
            try:
                validate_environment_name(name)  # type: ignore
                break
            except ValueError as e:
                reason = str(e)
                rich.print(f"[red]{reason}[/red]")
                name = beaupy.prompt("Please enter a new Environment name.")
    else:
        validate_environment_name(name)

    environment_manager = EnvironmentManager(
        # NOTE: We use config.project so ENV variables are included
        project_name=config.project,
        environment_name=name,  # type: ignore
        backend=config.launchflow_yaml.backend,
    )
    try:
        environment = await create_environment(
            env_type,
            cloud_provider=cloud_provider,
            manager=environment_manager,
            gcp_project_id=gcp_project_id,
            gcs_artifact_bucket=gcs_artifact_bucket,
            gcp_organization_name=gcp_organization_name,
            environment_service_account_email=gcp_service_account_email,
            prompt=not auto_approve,
        )
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if environment is not None:
        print_response(
            "\nEnvironment Info",
            environment.model_dump(
                mode="json", exclude_defaults=True, exclude_none=True
            ),
        )


@app.command()
async def list(
    output_format: OutputFormat = typer.Option(
        "default", "--format", "-f", help="Output format"
    ),
    expand_contents: bool = typer.Option(
        False, "--expand", "-e", help="List resources and services in the environments"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="The project name. If not provided, the current project is used.",
    ),
):
    """List all environments in the current directory's project."""
    if project is not None:
        # If the user passes the project flag, they most likely aren't in the project
        # directory so we set the backend to LaunchFlow Cloud if there's no launchflow.yaml file
        try:
            backend = config.launchflow_yaml.backend
        except exceptions.LaunchFlowYamlNotFound:
            logger.warning(
                "No launchflow.yaml file found. Using the default LaunchFlow Cloud Backend: 'lf://default'.\n"
            )
            backend = LaunchFlowBackend.parse_backend("lf://default")
    else:
        project = config.project
        backend = config.launchflow_yaml.backend

    manager = ProjectManager(
        # NOTE: We use config.project so ENV variables are included
        project_name=project,
        backend=backend,
    )
    try:
        envs = await manager.list_environments()
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not envs:
        rich.print("[yellow]No environments found.[/yellow]")
        return

    if output_format == OutputFormat.YAML:
        output_dict: Dict[str, Any] = {}
        for name, env in envs.items():
            env_manager = manager.create_environment_manager(name)

            output_dict[name] = {}
            output_dict[name]["environment"] = env.model_dump(
                mode="json", exclude_defaults=True, exclude_none=True
            )

            if expand_contents:
                resources = await env_manager.list_resources()
                resources.update(await env_manager.list_docker_resources())
                services = await env_manager.list_services()

                output_dict[name]["resources"] = {
                    name: resource.model_dump(
                        mode="json", exclude_defaults=True, exclude_none=True
                    )
                    for name, resource in resources.items()
                }
                output_dict[name]["services"] = {
                    name: service.model_dump(
                        mode="json", exclude_defaults=True, exclude_none=True
                    )
                    for name, service in services.items()
                }

        print(json_to_yaml(output_dict))
    else:
        print("Environments:")
        for name, env in envs.items():
            env_manager = manager.create_environment_manager(name)

            if env.gcp_config is not None:
                prefix = "GCPEnvironment"
            elif env.aws_config is not None:
                prefix = "AWSEnvironment"
            else:
                prefix = "Environment"
            print(f"- {prefix}(name='{name}', status='{env.status.value}')")
            if expand_contents:
                resources = await env_manager.list_resources()
                resources.update(await env_manager.list_docker_resources())
                if resources:
                    print("  - Resources:")
                    for name, resource in resources.items():
                        resource_cls = RESOURCE_PRODUCTS_TO_RESOURCES[resource.product]
                        print(f"    - {resource_cls.__name__}(name='{name}')")

                services = await env_manager.list_services()
                if services:
                    print("  - Services:")
                    for name, service in services.items():
                        service_cls = SERVICE_PRODUCTS_TO_SERVICES[service.product]
                        print(f"    - {service_cls.__name__}(name='{name}')")


@app.command()
async def get(
    name: Optional[str] = typer.Argument(None, help="The environment name."),
    output_format: OutputFormat = typer.Option(
        "default", "--format", "-f", help="Output format"
    ),
    expand_contents: bool = typer.Option(
        False, "--expand", "-e", help="List resources and services in the environment"
    ),
):
    """Get information about a specific environment."""
    if name is None:
        ps_manager = ProjectManager(
            backend=config.launchflow_yaml.backend, project_name=config.project
        )
        name, _ = await get_environment(
            ps_manager,
            environment_name=name,
            prompt_for_creation=False,
        )
    environment_manager = EnvironmentManager(
        # NOTE: We use config.project so ENV variables are included
        project_name=config.project,
        environment_name=name,
        backend=config.launchflow_yaml.backend,
    )
    try:
        env = await environment_manager.load_environment()
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if output_format == OutputFormat.YAML:
        output_dict: Dict[str, Any] = {}

        output_dict = {}
        output_dict["environment"] = env.model_dump(
            mode="json", exclude_defaults=True, exclude_none=True
        )

        if expand_contents:
            resources = await environment_manager.list_resources()
            resources.update(await environment_manager.list_docker_resources())
            services = await environment_manager.list_services()

            output_dict["resources"] = {
                name: resource.model_dump(
                    mode="json", exclude_defaults=True, exclude_none=True
                )
                for name, resource in resources.items()
            }
            output_dict["services"] = {
                name: service.model_dump(
                    mode="json", exclude_defaults=True, exclude_none=True
                )
                for name, service in services.items()
            }

        print(json_to_yaml(output_dict))
    else:
        if env.gcp_config is not None:
            prefix = "GCPEnvironment"
        elif env.aws_config is not None:
            prefix = "AWSEnvironment"
        else:
            prefix = "Environment"
        print(f"{prefix}(name='{name}', status='{env.status.value}')")


@app.command()
async def delete(
    name: Optional[str] = typer.Argument(None, help="The environment name."),
    detach: bool = typer.Option(
        False,
        help="If true we will not clean up any of the cloud resources associated with the environment and will simply delete the record from LaunchFlow.",
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve environment deletion."
    ),
    # TODO: Update the other commands to support the project flag (when it makes sense)
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="The project name. If not provided, the current project is used.",
    ),
):
    """Delete an environment."""
    if project is not None:
        # If the user passes the project flag, they most likely aren't in the project
        # directory so we set the backend to LaunchFlow Cloud if there's no launchflow.yaml file
        try:
            backend = config.launchflow_yaml.backend
        except exceptions.LaunchFlowYamlNotFound:
            logger.warning(
                "No launchflow.yaml file found. Using the default LaunchFlow Cloud Backend: 'lf://default'.\n"
            )
            backend = LaunchFlowBackend.parse_backend("lf://default")
    else:
        project = config.project
        backend = config.launchflow_yaml.backend

    if name is None:
        ps_manager = ProjectManager(backend=backend, project_name=project)
        name, _ = await get_environment(
            ps_manager,
            environment_name=name,
            prompt_for_creation=False,
            allow_failed=True,
        )
    environment_manager = EnvironmentManager(
        # NOTE: We use config.project so ENV variables are included
        project_name=project,
        environment_name=name,
        backend=backend,
    )
    try:
        await environment_manager.load_environment()
    except exceptions.EnvironmentNotFound:
        rich.print(f"[red]Environment '{name}' not found.[/red]")
        raise typer.Exit(1)
    try:
        await delete_environment(
            manager=environment_manager, detach=detach, prompt=not auto_approve
        )
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
async def unlock(
    name: str = typer.Argument(..., help="The environment to unlock."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve environment force unlock."
    ),
    include_services: bool = typer.Option(
        False, "--include-services", help="Include services in the unlock."
    ),
    include_resources: bool = typer.Option(
        False, "--include-resources", help="Include resources in the unlock."
    ),
):
    """Force unlock an environment."""
    environment_manager = EnvironmentManager(
        # NOTE: We use config.project so ENV variables are included
        project_name=config.project,
        environment_name=name,
        backend=config.launchflow_yaml.backend,
    )
    to_raise = None
    if not auto_approve:
        rich.print(
            f"[yellow]Are you sure you want to force unlock environment '{name}'? This can lead to data corruption or conflicts.[/yellow]"
        )
        # TODO: Link to docs that explain what force unlock does
        if not beaupy.confirm("Force unlock environment?"):
            rich.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    try:
        await environment_manager.force_unlock_environment()
        rich.print(f"[green]Environment '{name}' force unlocked.[/green]")
    except (exceptions.EntityNotLocked, exceptions.LockNotFound):
        rich.print(
            f"[yellow]Environment '{name}' is not locked. Nothing to unlock.[/yellow]"
        )
        to_raise = typer.Exit(1)
    except Exception as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        rich.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if include_resources:
        if not auto_approve:
            rich.print(
                f"\n[yellow]Are you sure you want to force unlock resources in environment '{name}'? This can lead to data corruption or conflicts.[/yellow]"
            )
            # TODO: Link to docs that explain what force unlock does
            if not beaupy.confirm("Force unlock all resources in environment?"):
                rich.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

        resources = await environment_manager.list_resources()
        for resource_name in resources:
            resource_manager = environment_manager.create_resource_manager(
                resource_name
            )
            try:
                await resource_manager.force_unlock_resource()
                rich.print(
                    f"[green]Resource '{resource_name}' force unlocked in Environment '{name}'.[/green]"
                )
            except (exceptions.EntityNotLocked, exceptions.LockNotFound):
                rich.print(
                    f"[yellow]Resource '{resource_name}' is not locked. Nothing to unlock.[/yellow]"
                )
                to_raise = typer.Exit(1)
            except Exception as e:
                logging.debug("Exception occurred: %s", e, exc_info=True)
                rich.print(f"[red]{e}[/red]")
                raise typer.Exit(1)

    if include_services:
        if not auto_approve:
            rich.print(
                f"\n[yellow]Are you sure you want to force unlock services in environment '{name}'? This can lead to data corruption or conflicts.[/yellow]"
            )
            # TODO: Link to docs that explain what force unlock does
            if not beaupy.confirm("Force unlock all services in environment?"):
                rich.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

        services = await environment_manager.list_services()
        for service_name in services:
            service_manager = environment_manager.create_service_manager(service_name)
            try:
                await service_manager.force_unlock_service()
                rich.print(
                    f"[green]Service '{service_name}' force unlocked in Environment '{name}'.[/green]"
                )
            except (exceptions.EntityNotLocked, exceptions.LockNotFound):
                rich.print(
                    f"[yellow]Service '{service_name}' is not locked. Nothing to unlock.[/yellow]"
                )
                to_raise = typer.Exit(1)
            except Exception as e:
                logging.debug("Exception occurred: %s", e, exc_info=True)
                rich.print(f"[red]{e}[/red]")
                raise typer.Exit(1)

    if to_raise:
        raise to_raise
