import asyncio
import logging
import os
import shlex
import signal
from typing import Any, List, Optional, Set

import rich
import typer
import uvloop
from rich.progress import Progress, SpinnerColumn, TextColumn
from terminaltexteffects.effects.effect_wipe import Wipe

import launchflow
from launchflow import exceptions
from launchflow.cache.launchflow_tmp import (
    build_cache_key,
    encode_resource_outputs_cache,
)
from launchflow.cli import project_gen
from launchflow.cli.accounts import account_commands
from launchflow.cli.ast_search import (
    find_launchflow_resources,
    find_launchflow_services,
)
from launchflow.cli.cloud import cloud_commands
from launchflow.cli.constants import (
    API_KEY_HELP,
    ENVIRONMENT_HELP,
    SCAN_DIRECTORY_HELP,
    SERVICE_DEPLOY_HELP,
    SERVICE_PROMOTE_HELP,
)
from launchflow.cli.environments import environment_commands
from launchflow.cli.project import project_commands
from launchflow.cli.resource_utils import (
    deduplicate_resources,
    import_resources,
    is_local_resource,
)
from launchflow.cli.resources import resource_commands
from launchflow.cli.secrets import secret_commands
from launchflow.cli.service_utils import deduplicate_services, import_services
from launchflow.cli.services import service_commands
from launchflow.cli.utyper import UTyper
from launchflow.clients import async_launchflow_client_ctx
from launchflow.clients.docker_client import docker_service_available
from launchflow.config import config
from launchflow.dependencies.opentofu import install_opentofu, needs_opentofu
from launchflow.docker.resource import DockerResource
from launchflow.exceptions import LaunchFlowRequestFailure
from launchflow.flows.auth import login_flow, logout_flow
from launchflow.flows.create_flows import create as create_resources
from launchflow.flows.deploy_flows import deploy as deploy_services
from launchflow.flows.deploy_flows import promote as promote_services
from launchflow.flows.environments_flows import get_environment
from launchflow.flows.resource_flows import destroy as destroy_resources
from launchflow.flows.resource_flows import (
    import_existing_resources,
    stop_local_containers,
)
from launchflow.logger import logger
from launchflow.managers.project_manager import ProjectManager
from launchflow.node import Outputs
from launchflow.resource import Resource

app = UTyper(
    help="CLI for interacting with LaunchFlow. Use the LaunchFlow CLI to create and manage your cloud environments and resources.",
    no_args_is_help=True,
)
app.add_typer(account_commands.app, name="accounts")
app.add_typer(project_commands.app, name="projects")
app.add_typer(environment_commands.app, name="environments")
app.add_typer(resource_commands.app, name="resources")
app.add_typer(service_commands.app, name="services")
app.add_typer(secret_commands.app, name="secrets")
app.add_typer(cloud_commands.app, name="cloud")


@app.callback()
def cli_setup(
    disable_usage_statistics: bool = typer.Option(
        False, help="If true no usage statistics will be collected."
    ),
    log_level: Optional[str] = None,
):
    if log_level is not None:
        logger.setLevel(log_level.upper())
    if needs_opentofu():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Installing dependencies...", total=1)
            install_opentofu()
            rich.print("[green]✓[/green] Dependencies installed.")
            progress.remove_task(task)


def _set_global_project_and_environment(
    project: Optional[str], environment: Optional[str]
):
    if project is not None:
        launchflow.project = project
    else:
        launchflow.project = config.project
    if environment is not None:
        launchflow.environment = environment
    else:
        launchflow.environment = config.environment


_LAUNCHFLOW_TEXT = r""" _                                 _      _____  _
| |                               | |    |  ___|| |
| |      __ _  _   _  _ __    ___ | |__  | |_   | |  ___ __      __
| |     / _` || | | || '_ \  / __|| '_ \ |  _|  | | / _ \\ \ /\ / /
| |____| (_| || |_| || | | || (__ | | | || |    | || (_) |\ V  V /
\_____/ \__,_| \__,_||_| |_| \___||_| |_|\_|    |_| \___/  \_/\_/

"""


@app.command()
async def init(
    default_backend: Optional[project_gen.BackendType] = typer.Option(
        None, "--backend", "-b", help="The backend to use for the project."
    ),
):
    """Initialize a new launchflow project."""
    # Validation for the init options
    if default_backend == project_gen.BackendType.GCS:
        typer.echo("The GCS backend is not supported yet.")
        raise typer.Exit(1)

    effect = Wipe(_LAUNCHFLOW_TEXT)
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)

    try:
        # generates a launchflow.yaml file
        await project_gen.generate_launchflow_yaml(default_backend_type=default_backend)

        # (optionally) generates an infra.py file
        project_gen.generate_infra_dot_py()

    except typer.Exit:
        return
    except Exception as e:
        rich.print(f"[red]✗ Failed to configure project.[/red] {e}")
        rich.print(
            "\nIf the error persists, please open an issue on GitHub or contact the LaunchFlow team.\n"
        )
        rich.print(
            "GitHub Issues: [blue]https://github.com/launchflow/launchflow/issues[/blue]"
        )
        rich.print("LaunchFlow Contact: [blue]team@launchflow.com[/blue]\n")
        raise typer.Exit(1)

    rich.print("\n[green]Your project is configured and ready for launch[/green] 🚀\n")

    rich.print("[bold]Docs:[/bold] [blue]https://docs.launchflow.com[/blue]")
    rich.print("[bold]Console:[/bold] [blue]https://console.launchflow.com[/blue]")
    rich.print(
        "[bold]Quickstart:[/bold] [blue]https://docs.launchflow.com/docs/quickstart[/blue]\n"
    )


async def _handle_no_launchflow_yaml_found(auto_approve: bool):
    try:
        backend = config.launchflow_yaml.backend
    except exceptions.LaunchFlowYamlNotFound:
        if auto_approve:
            typer.echo("No launchflow.yaml found. Please run `lf init` then try again.")
            raise typer.Exit(1)
        rich.print("[red]No launchflow.yaml found.[/red]")
        answer = typer.confirm("Would you like to create one now?")
        if not answer:
            typer.echo("Exiting.")
            raise typer.Exit(1)
        await project_gen.generate_launchflow_yaml(default_backend_type=None)
        try:
            backend = config.launchflow_yaml.backend
            _set_global_project_and_environment(
                config.launchflow_yaml.project,
                config.launchflow_yaml.default_environment,
            )
            typer.echo("launchflow.yaml created successfully.")
        except exceptions.LaunchFlowYamlNotFound:
            typer.echo("Failed to create launchflow.yaml. Exiting.")
            raise typer.Exit(1)
    return backend


async def _create_resources(
    resources_to_create: Set[str],
    services_to_create: Set[str],
    environment: str,
    scan_directory: str,
    auto_approve: bool,
    local_only: bool,
    remote_only: bool,
    verbose: bool,
):
    if local_only and remote_only:
        typer.echo("Internal error: local_only and remote_only cannot both be true.")
        raise typer.Exit(1)

    resource_refs = find_launchflow_resources(
        scan_directory, ignore_roots=config.ignore_roots
    )
    resources = import_resources(resource_refs)
    resources = deduplicate_resources(resources)  # type: ignore

    if resources_to_create:
        resources = [
            resource for resource in resources if resource.name in resources_to_create
        ]

    service_refs = find_launchflow_services(
        scan_directory, ignore_roots=config.ignore_roots
    )
    services = import_services(service_refs)
    services = deduplicate_services(services)  # type: ignore

    if services_to_create:
        services = [
            service for service in services if service.name in services_to_create
        ]

    if local_only:
        resources = [resource for resource in resources if is_local_resource(resource)]
    elif remote_only:
        resources = [
            resource for resource in resources if not is_local_resource(resource)
        ]

    try:
        success = await create_resources(
            *resources,  # type: ignore
            *services,  # type: ignore
            environment=environment,
            prompt=not auto_approve,
            verbose=verbose,
        )
        if not success:
            raise typer.Exit(1)
        print()

    except LaunchFlowRequestFailure as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        e.pretty_print()
        raise typer.Exit(1)


@app.command()
async def create(
    environment: Optional[str] = typer.Argument(None, help=ENVIRONMENT_HELP),
    resource: List[str] = typer.Option(
        default_factory=list,
        help="Resource name to create. If none we will scan the directory for available resources. This can be specified multiple times to create multiple resources.",
    ),
    service: List[str] = typer.Option(
        default_factory=list,
        help="Service name to create. If none we will scan the directory for available services. This can be specified multiple times to create multiple services.",
    ),
    scan_directory: str = typer.Option(
        ".", "--scan-directory", "-d", help=SCAN_DIRECTORY_HELP
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve resource creation."
    ),
    local_only: bool = typer.Option(
        False, "--local", help="Create only local resources."
    ),
    launchflow_api_key: Optional[str] = typer.Option(None, help=API_KEY_HELP),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="If set all logs will be written to stdout."
    ),
):
    """Create any resources that are not already created."""
    backend = await _handle_no_launchflow_yaml_found(auto_approve)
    if launchflow_api_key:
        config.set_api_key(launchflow_api_key)

    # NOTE: this needs to be before we import the resources
    if environment is None:
        environment, _ = await get_environment(
            project_state_manager=ProjectManager(
                backend=backend,
                project_name=launchflow.project,
            ),
            environment_name=environment,
            prompt_for_creation=True,
        )
    _set_global_project_and_environment(None, environment)

    await _create_resources(
        resources_to_create=set(resource),
        services_to_create=set(service),
        environment=environment,
        scan_directory=scan_directory,
        auto_approve=auto_approve,
        local_only=local_only,
        remote_only=False,
        verbose=verbose,
    )


@app.command()
async def destroy(
    environment: Optional[str] = typer.Argument(None, help=ENVIRONMENT_HELP),
    resource: List[str] = typer.Option(
        default_factory=list,
        help="Resource name to destroy. If none we will scan the directory for available resources. This can be specified multiple times to destroy multiple resources.",
    ),
    service: List[str] = typer.Option(
        default_factory=list,
        help="Service name to destroy. If none we will scan the directory for available services. This can be specified multiple times to destroy multiple services.",
    ),
    local_only: bool = typer.Option(
        False, "--local", help="Only destroy local resources."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve resource destruction."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="If set all logs will be written to stdout."
    ),
    launchflow_api_key: Optional[str] = typer.Option(None, help=API_KEY_HELP),
    detach: bool = typer.Option(
        False,
        help="If true we will not clean up any of the cloud resources associated with the environment and will simply delete the record from LaunchFlow.",
    ),
):
    """Destroy all resources in the project / environment."""
    if local_only and not docker_service_available():
        raise exceptions.MissingDockerDependency(
            "Docker is required to use the `--local-only` flag."
        )
    if launchflow_api_key:
        config.set_api_key(launchflow_api_key)
    # NOTE: this needs to be before we import the resources
    if environment is None:
        environment, _ = await get_environment(
            project_state_manager=ProjectManager(
                backend=config.launchflow_yaml.backend,
                project_name=config.project,
            ),
            environment_name=environment,
            prompt_for_creation=False,
        )
    _set_global_project_and_environment(None, environment)

    try:
        result = await destroy_resources(
            environment,
            resources_to_destroy=set(resource),
            services_to_destroy=set(service),
            local_only=local_only,
            prompt=not auto_approve,
            verbose=verbose,
            detach=detach,
        )
        if not result:
            raise typer.Exit(1)
    except LaunchFlowRequestFailure as e:
        logging.debug("Exception occurred: %s", e, exc_info=True)
        e.pretty_print()
        raise typer.Exit(1)


@app.command(hidden=True)
async def deploy(
    environment: Optional[str] = typer.Argument(None, help=ENVIRONMENT_HELP),
    service: List[str] = typer.Option(default_factory=list, help=SERVICE_DEPLOY_HELP),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve the deployment."
    ),
    skip_build: bool = typer.Option(
        False,
        help="If true the service will not be built, and the currently deployed build will be used.",
    ),
    launchflow_api_key: Optional[str] = typer.Option(None, help=API_KEY_HELP),
    scan_directory: str = typer.Option(".", help=SCAN_DIRECTORY_HELP),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output. Will include all options provided to your service.",
    ),
    build_local: bool = typer.Option(
        False,
        "--build-local",
        help="Build the Docker image locally.",
    ),
    skip_create: bool = typer.Option(
        False,
        "--skip-create",
        help="Skip the Resource creation step.",
    ),
    check_dockerfiles: bool = typer.Option(
        False,
        "--check-dockerfiles",
        help="Ensure that Service Dockerfiles exist before deploying.",
    ),
):
    """Deploy a service to a project / environment."""
    backend = await _handle_no_launchflow_yaml_found(auto_approve)
    if launchflow_api_key:
        config.set_api_key(launchflow_api_key)

    if environment is None:
        environment, _ = await get_environment(
            project_state_manager=ProjectManager(
                backend=backend,
                project_name=launchflow.project,
            ),
            environment_name=environment,
            prompt_for_creation=True,
        )
    _set_global_project_and_environment(None, environment)

    resource_refs = find_launchflow_resources(
        scan_directory, ignore_roots=config.ignore_roots
    )
    resources = import_resources(resource_refs)
    resources = deduplicate_resources(resources)  # type: ignore

    service_refs = find_launchflow_services(
        scan_directory, ignore_roots=config.ignore_roots
    )
    services = import_services(service_refs)
    services = deduplicate_services(services)  # type: ignore

    service_set = set(service)
    if service_set:
        services = [s for s in services if s.name in service_set]

    if not services:
        typer.echo("No services found. Nothing to deploy.")
        raise typer.Exit(1)

    result = await deploy_services(
        *resources,  # type: ignore
        *services,  # type: ignore
        environment=environment,
        prompt=not auto_approve,
        verbose=verbose,
        build_local=build_local,
        skip_create=skip_create,
        check_dockerfiles=check_dockerfiles,
        skip_build=skip_build,
    )
    if not result.success:
        raise typer.Exit(1)


@app.command(hidden=True)
async def promote(
    from_environment: str = typer.Argument(
        ..., help="The environment to promote from."
    ),
    to_environment: str = typer.Argument(..., help="The environment to promote to"),
    service: List[str] = typer.Option(default_factory=list, help=SERVICE_PROMOTE_HELP),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto approve the deployment."
    ),
    launchflow_api_key: Optional[str] = typer.Option(None, help=API_KEY_HELP),
    promote_local: bool = typer.Option(
        False,
        help="Promote the service locally. If true this will move the docker image to the new environment locally instead of on Cloud Build or Code Build.",
    ),
    scan_directory: str = typer.Option(".", help=SCAN_DIRECTORY_HELP),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output. Will include all options provided to your service.",
    ),
):
    """Promote a service. This will take the image that is running in `from_environment` and promote it to a service in `to_environment`."""
    if launchflow_api_key:
        config.set_api_key(launchflow_api_key)
    _set_global_project_and_environment(None, to_environment)

    service_refs = find_launchflow_services(
        scan_directory, ignore_roots=config.ignore_roots
    )
    services = import_services(service_refs)

    service_set = set(service)
    if service_set:
        services = [s for s in services if s.name in service_set]

    if not services:
        typer.echo("No services found. Nothing to promote.")
        raise typer.Exit(1)

    result = await promote_services(
        *services,  # type: ignore
        from_environment=from_environment,
        to_environment=to_environment,
        prompt=not auto_approve,
        verbose=verbose,
        promote_local=promote_local,
    )
    if not result or not result.success:
        raise typer.Exit(1)


@app.command()
async def login():
    """Login to LaunchFlow. If you haven't signup this will create a free account for you."""
    try:
        async with async_launchflow_client_ctx(None) as client:
            await login_flow(client)
    except Exception as e:
        typer.echo(f"Failed to login. {e}")
        typer.Exit(1)


@app.command()
def logout():
    """Logout of LaunchFlow."""
    try:
        logout_flow()
    except Exception as e:
        typer.echo(f"Failed to logout: {e}")
        typer.Exit(1)


@app.command(hidden=True, name="import")
async def import_resource_cmd(
    environment: Optional[str] = typer.Argument(None, help=ENVIRONMENT_HELP),
    resource: Optional[str] = typer.Option(
        None,
        help="Resource name to import. If none we will scan the directory for available resources.",
    ),
    scan_directory: str = typer.Option(".", help=SCAN_DIRECTORY_HELP),
):
    if environment is None:
        environment, _ = await get_environment(
            project_state_manager=ProjectManager(
                backend=config.launchflow_yaml.backend,
                project_name=config.project,
            ),
            environment_name=environment,
            prompt_for_creation=True,
        )
    _set_global_project_and_environment(None, environment)
    resource_refs = find_launchflow_resources(
        scan_directory, ignore_roots=config.ignore_roots
    )
    service_refs = find_launchflow_services(
        scan_directory, ignore_roots=config.ignore_roots
    )
    resources = import_resources(resource_refs)
    services = import_services(service_refs)
    for service in services:
        resources.extend(service.resources())

    if resource:
        resources = [r for r in resources if r.name == resource]

    success = await import_existing_resources(environment, *resources)  # type: ignore
    if not success:
        raise typer.Exit(1)


async def _connect_resources_not_found_okay(
    *resources: Resource,
) -> List[Outputs]:
    async def connect_not_found_okay(resource: Resource) -> Optional[Outputs]:
        try:
            return await resource.outputs_async()
        except exceptions.ResourceNotFound:
            return None

    connect_tasks = [connect_not_found_okay(resource) for resource in resources]
    return [r for r in await asyncio.gather(*connect_tasks) if r is not None]


# TODO: Update this flow to use the FlowLogger
# TODO: Would be nice to have environment be optional, but typer makes it difficult/messy
@app.command()
async def run(
    environment: str = typer.Argument(..., help=ENVIRONMENT_HELP),
    scan_directory: str = typer.Option(".", help=SCAN_DIRECTORY_HELP),
    args: Optional[List[str]] = typer.Argument(None, help="Additional command to run"),
    disable_run_cache: bool = typer.Option(
        False,
        "--disable-run-cache",
        help="Disable the run cache, Resource outputs will always be fetched.",
    ),
    launchflow_api_key: Optional[str] = typer.Option(None, help=API_KEY_HELP),
):
    """Run a command against an environment.

    Sample commands:

        lf run dev -- ./run.sh
            - Runs ./run.sh against dev environment resources.
    """
    await _handle_no_launchflow_yaml_found(auto_approve=False)
    _set_global_project_and_environment(None, environment)
    if launchflow_api_key:
        config.set_api_key(launchflow_api_key)

    resources_refs = find_launchflow_resources(
        scan_directory, ignore_roots=config.ignore_roots
    )
    resources = import_resources(resources_refs)

    resources = deduplicate_resources(resources)  # type: ignore

    local_resources: List[DockerResource[Any]] = [
        resource  # type: ignore
        for resource in resources
        if is_local_resource(resource)
    ]
    remote_resources: List[Resource[Any]] = [
        resource for resource in resources if not is_local_resource(resource)
    ]
    if local_resources or remote_resources:
        typer.echo("Creating resources...")
        await create_resources(*resources, environment=environment, prompt=True)  # type: ignore
        typer.echo("Created resources successfully.\n")

    if args is None or len(args) < 1:
        typer.echo("No command provided. Exiting")
        return

    current_env = os.environ.copy()
    current_env["LAUNCHFLOW_ENVIRONMENT"] = environment

    if remote_resources and not disable_run_cache:
        rich.print("Building run cache...")
        # Connects to all remote resources, and encodes their outputs as an env variable
        resource_outputs = await _connect_resources_not_found_okay(*remote_resources)
        resource_outputs_dict = {
            build_cache_key(
                project=launchflow.project,
                environment=environment,
                product=resource.product,
                resource=resource.name,
            ): outputs.to_dict()
            for resource, outputs in zip(remote_resources, resource_outputs)
            if outputs is not None
        }
        run_cache = encode_resource_outputs_cache(resource_outputs_dict)
        current_env["LAUNCHFLOW_RUN_CACHE"] = run_cache
        rich.print("Run cache built successfully.")

    command = args[0]
    command_args = []
    for arg in args[1:]:
        command_args.append(shlex.quote(arg))

    proc = await asyncio.create_subprocess_exec(command, *command_args, env=current_env)

    async def handle_shutdown():
        proc.terminate()
        await proc.wait()

    loop = asyncio.get_event_loop()

    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_shutdown()))

    rich.print("───── Program Output ─────")
    rich.print()
    try:
        await proc.communicate()
    except asyncio.CancelledError:
        # TODO: I don't like this sleep but for some reason it starts before the above process has finished printing
        await asyncio.sleep(1)
    finally:
        try:
            proc.terminate()
            await proc.wait()
        except ProcessLookupError:
            # Swallow exception if process has already been stopped
            pass
        rich.print("\n──────────────────────────")
        typer.echo("\nStopping running local resources...")
        local_container_ids = [
            resource.running_container_id
            for resource in local_resources
            if resource.running_container_id is not None
        ]
        await stop_local_containers(local_container_ids, prompt=False)
        typer.echo("\nStopped local resources successfully.")


@app.command()
def version():
    """Print the version of launchflow."""
    typer.echo(launchflow.__version__)


if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app()
