import os
from enum import Enum
from typing import Optional

import beaupy  # type: ignore
import rich
import typer

from launchflow import exceptions
from launchflow.aws.elasticache import ElasticacheRedis
from launchflow.aws.rds import RDS
from launchflow.aws.s3 import S3Bucket
from launchflow.backend import BackendOptions, LaunchFlowBackend, LocalBackend
from launchflow.clients import async_launchflow_client_ctx
from launchflow.config import config
from launchflow.config.launchflow_yaml import LaunchFlowDotYaml
from launchflow.docker.postgres import DockerPostgres
from launchflow.docker.redis import DockerRedis
from launchflow.flows.auth import login_flow
from launchflow.flows.lf_cloud_migration import migrate
from launchflow.flows.project_flows import get_project
from launchflow.gcp.cloudsql import CloudSQLPostgres
from launchflow.gcp.compute_engine import ComputeEngineRedis
from launchflow.gcp.gcs import GCSBucket
from launchflow.gcp.memorystore import MemorystoreRedis
from launchflow.validation import validate_project_name


class BackendType(Enum):
    LOCAL = "local"
    GCS = "gcs"
    LAUNCHFLOW = "lf"


class Framework(Enum):
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"


FRAMEWORK_CHOICES = [
    (
        Framework.FASTAPI,
        "FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
    ),
    (
        Framework.FLASK,
        "The Python micro framework for building web applications.",
    ),
    (
        Framework.DJANGO,
        "The Web framework for perfectionists with deadlines.",
    ),
]


class InfrastructureProvider(Enum):
    GCP = "GCP"
    AWS = "AWS"
    Docker = "Docker"


INFRASTRUCTURE_PROVIDER_CHOICES = [
    (InfrastructureProvider.GCP, "Google Cloud Platform"),
    (InfrastructureProvider.AWS, "Amazon Web Services"),
    (InfrastructureProvider.Docker, "Docker Engine (localhost)"),
]


GCP_RESOURCE_CHOICES = [
    (
        GCSBucket,
        "Storage bucket. Powered by Google Cloud Storage (GCS).",
    ),
    (
        CloudSQLPostgres,
        "PostgreSQL database. Powered by Cloud SQL on GCP.",
    ),
    (
        ComputeEngineRedis,
        "Redis on a VM. Powered by Compute Engine on GCP.",
    ),
    (
        MemorystoreRedis,
        "Redis Cluster. Powered by Memorystore on GCP.",
    ),
]

AWS_RESOURCE_CHOICES = [
    (
        S3Bucket,
        "Storage bucket. Powered by Amazon S3.",
    ),
    (
        RDS,
        "PostgreSQL database. Powered by Amazon RDS.",
    ),
    (
        ElasticacheRedis,
        "Redis Cluster. Powered by Amazon ElastiCache.",
    ),
]

DOCKER_RESOURCE_CHOICES = [
    (
        DockerPostgres,
        "PostgreSQL database. Running locally on Docker.",
    ),
    (
        DockerRedis,
        "Redis instance. Running locally on Docker.",
    ),
]


def _select_backend() -> Optional[BackendType]:
    options = [
        "Local - State will be saved in your project directory",
        "LaunchFlow Cloud - State will be managed for you and shared with teammates",
    ]
    rich.print("How would you like to manage your infrastructure state?")
    answer = beaupy.select(options=options, return_index=True)
    if answer is None:
        typer.echo("No backend selected. Exiting.")
        raise typer.Exit(1)
    if answer == 0:
        rich.print("[pink1]>[/pink1] Local\n")
        return BackendType.LOCAL
    rich.print("[pink1]>[/pink1] LaunchFlow Cloud\n")
    return BackendType.LAUNCHFLOW


def maybe_append_file_to_gitignore(file_name: str, gitignore_path=".gitignore"):
    need_to_append = True

    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as gitignore_file:
            gitignore_contents = gitignore_file.readlines()

        for line in gitignore_contents:
            line = line.strip()
            if line == file_name or (line.endswith("/") and file_name.startswith(line)):
                need_to_append = False
                break

    if need_to_append:
        with open(gitignore_path, "a") as gitignore_file:
            gitignore_file.write(f"\n# LaunchFlow\n{file_name}\n")


async def generate_launchflow_yaml(
    default_backend_type: Optional[BackendType],
):
    try:
        existing_backend = config.launchflow_yaml.backend
        existing_project_name = config.launchflow_yaml.project
        existing_backend_options = config.launchflow_yaml.backend_options
    except exceptions.LaunchFlowYamlNotFound:
        existing_backend = None
        existing_project_name = None
        existing_backend_options = None

    backend_options = BackendOptions()
    if existing_backend_options is not None:
        backend_options = existing_backend_options

    print("Welcome to LaunchFlow! 🚀")
    print("This tool will help you configure your launchflow.yaml file.\n")

    if existing_backend is not None:
        rich.print("[yellow]A launchflow.yaml file already exists.[/yellow]")
        overwrite = beaupy.confirm(
            "Would you like to reconfigure the existing launchflow.yaml?",
            default_is_yes=False,
        )
        if not overwrite:
            typer.echo("Reusing the existing launchflow.yaml. No changes will be made.")
            return
        print("Would you like to reconfigure the existing launchflow.yaml?")
        rich.print("[pink1]>[/pink1] Yes\n")

    backend_type = default_backend_type
    if backend_type is None:
        backend_type = _select_backend()

    if backend_type == BackendType.LAUNCHFLOW:
        if isinstance(existing_backend, LaunchFlowBackend):
            rich.print(
                "[yellow]This project is already configured to use LaunchFlow Cloud. No changes will be made.[/yellow]"
            )
            return

        login_or_signup = False
        if config.credentials is None:
            rich.print("[yellow]No LaunchFlow Cloud credentials found.[/yellow]")
            login_or_signup = beaupy.confirm(
                "Would you like to login / sign up for LaunchFlow Cloud? It's free!",
                default_is_yes=True,
            )
            if not login_or_signup:
                typer.echo("Exiting.")
                raise typer.Exit(1)
            print("Would you like to login / sign up for LaunchFlow Cloud? It's free!")
            rich.print("[pink1]>[/pink1] Yes")
        else:
            # NOTE: We only try to refresh creds if the user is already logged in.
            try:
                config.get_access_token()
            except exceptions.LaunchFlowRequestFailure:
                rich.print("[red]Failed to refresh LaunchFlow credentials.[/red]")
                login_or_signup = beaupy.confirm(
                    "Would you like to re-login to LaunchFlow?",
                    default_is_yes=True,
                )
                if not login_or_signup:
                    typer.echo("Exiting.")
                    raise typer.Exit(1)
                print("Would you like to re-login to LaunchFlow?")
                rich.print("[pink1]>[/pink1] Yes")
            except exceptions.NoLaunchFlowCredentials:
                rich.print("[red]No LaunchFlow credentials found.[/red]")
                login_or_signup = beaupy.confirm(
                    "Would you like to login / sign up for LaunchFlow? It's free!",
                    default_is_yes=True,
                )
                if not login_or_signup:
                    typer.echo("Exiting.")
                    raise typer.Exit(1)
                print("Would you like to login / sign up for LaunchFlow? It's free!")
                rich.print("[pink1]>[/pink1] Yes")

        if login_or_signup:
            async with async_launchflow_client_ctx(None) as client:
                await login_flow(client)

        async with async_launchflow_client_ctx(None) as client:
            accounts = await client.accounts.list()
            if len(accounts) == 0:
                rich.print("[red]Failed to fetch LaunchFlow accounts.[/red]")
                rich.print(
                    "Please contact team@launchflow.com if the issue persists.\n"
                )
                raise typer.Exit(1)
            elif len(accounts) > 1:
                rich.print("Which LaunchFlow account would you like to use?")
                account_id = beaupy.select(
                    [account.id for account in accounts], strict=True
                )
                if account_id is None:
                    rich.print("No account selected. Exiting.")
                    raise typer.Exit(1)
                rich.print(f"[pink1]>[/pink1] {account_id}")
                account_id_for_config = account_id
            else:
                account_id = accounts[0].id
                account_id_for_config = "default"

        backend = LaunchFlowBackend.parse_backend(
            f"lf://{account_id_for_config}", backend_options
        )

        migrate_to_launchflow = False
        if (
            isinstance(existing_backend, LocalBackend)
            and existing_project_name is not None
        ):
            migrate_to_launchflow = beaupy.confirm(
                "Would you like to migrate your local project state to LaunchFlow Cloud?",
                default_is_yes=True,
            )
            rich.print(
                "Would you like to migrate your local project state to LaunchFlow Cloud?"
            )
            if migrate_to_launchflow:
                rich.print("[pink1]>[/pink1] Yes")
                await migrate(source=existing_backend, target=backend)
                rich.print(
                    "[green]Project state successfully migrated to LaunchFlow Cloud.[/green]"
                )
                project_name = existing_project_name
            else:
                rich.print("[pink1]>[/pink1] No")

        if not migrate_to_launchflow:
            async with async_launchflow_client_ctx(
                launchflow_account_id=account_id
            ) as client:
                project = await get_project(
                    client=client.projects,
                    account_id=account_id,
                    project_name=None,
                    prompt_for_creation=True,
                    custom_selection_prompt="Select an existing LaunchFlow Cloud project to use, or create a new one:",
                )
                if project is None:
                    typer.echo("Project creation canceled.")
                    raise typer.Exit(1)
                project_name = project.name

    else:
        if isinstance(existing_backend, LocalBackend):
            rich.print(
                "[yellow]This project is already configured to use local state. No changes will be made.[/yellow]"
            )
            return

        project_name = beaupy.prompt(
            "What would you like to name your LaunchFlow project?"
        )
        while True:
            try:
                validate_project_name(project_name)
                break
            except ValueError as e:
                reason = str(e)
                rich.print(f"[red]{reason}[/red]")
                project_name = beaupy.prompt("Please enter a new project name.")
        print("What would you like to name your LaunchFlow project?")
        rich.print(f"[pink1]>[/pink1] {project_name}\n")

        backend = LocalBackend.parse_backend("file://.launchflow")  # type: ignore

    config_path = os.path.join(os.getcwd(), "launchflow.yaml")
    launchflow_yaml = LaunchFlowDotYaml(
        project=project_name,
        backend=backend,
        backend_options=backend_options,
        default_environment=None,
        config_path=config_path,
    )
    launchflow_yaml.save()

    # Append to the gitignore (if .launchflow is not already in the gitignore)
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    maybe_append_file_to_gitignore(
        file_name=".launchflow", gitignore_path=gitignore_path
    )


def _select_framework() -> Framework:
    options = [f"{f[0].value} - {f[1]}" for f in FRAMEWORK_CHOICES]
    print()
    print("Select a framework for your API: (More coming soon)")
    answer = beaupy.select(options=options, return_index=True, strict=True)
    if answer is None:
        typer.echo("No framework selected. Exiting.")
        raise typer.Exit(1)
    rich.print(f"[pink1]>[/pink1] {options[answer]}")
    return FRAMEWORK_CHOICES[answer][0]


def _select_infra_provider() -> Optional[InfrastructureProvider]:
    answer = beaupy.confirm(
        "Would you like to add any infrastructure to your project?",
        default_is_yes=True,
    )
    if not answer:
        typer.echo("No infrastructure selected. Continuing without infrastructure.")
        return None

    options = [f"{f[0].value} - {f[1]}" for f in INFRASTRUCTURE_PROVIDER_CHOICES]
    print()
    print(
        "Select the infrastructure provider you'd like to use. You can always change providers later."
    )
    answer = beaupy.select(options=options, return_index=True, strict=True)
    if answer is None:
        typer.echo(
            "No infrastructure provider selected. Continuing without infrastructure."
        )
        return None
    return INFRASTRUCTURE_PROVIDER_CHOICES[answer][0]


# TODO: Implement template project generation
async def generate_template_project(
    template_id: str,
    default_backend: Optional[BackendType] = None,
):
    raise NotImplementedError("The template project feature is not implemented yet.")


# TODO: Implement bootstrap project generation
async def generate_bootstrap_project(
    default_backend: Optional[BackendType] = None,
):
    raise NotImplementedError("The bootstrap project feature is not implemented yet.")
