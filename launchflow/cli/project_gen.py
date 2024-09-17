import os
import re
from enum import Enum
from typing import Optional, Union

import beaupy  # type: ignore
import rich
import typer
from rich.syntax import Syntax

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
        "LaunchFlow Cloud",
        "Local Directory",
        # "GCS Bucket - State will be saved in a Google Cloud Storage bucket",
        # "S3 Bucket - State will be saved in an Amazon S3 bucket",
    ]
    rich.print("How would you like to manage your deployment state?")
    answer = beaupy.select(options=options, return_index=True)
    if answer is None:
        rich.print("[pink1]No backend selected.[/pink1]")
        return None
    if answer == 1:
        rich.print("[pink1]>[/pink1] Local Directory\n")
        return BackendType.LOCAL
    rich.print("[pink1]>[/pink1] LaunchFlow Cloud")
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
    console: rich.console.Console = rich.console.Console(),
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

    console.print("[bold]Welcome to LaunchFlow![/bold] 🚀")
    console.print(
        "This tool will help you configure your project to deploy to AWS or GCP.\n"
    )

    if existing_backend is not None:
        console.print("[yellow]A launchflow.yaml file already exists.[/yellow]")
        overwrite = beaupy.confirm(
            "Would you like to reconfigure the existing [bold]launchflow.yaml[/bold]?",
            default_is_yes=False,
        )

        console.print(
            "Would you like to reconfigure the existing [bold]launchflow.yaml[/bold]?"
        )
        if not overwrite:
            console.print("[pink1]>[/pink1] No\n")
            return
        console.print("[pink1]>[/pink1] Yes\n")

    backend_type = default_backend_type
    if backend_type is None:
        backend_type = _select_backend()
        if backend_type is None:
            console.print("\n[red]✗ Selecting a backend is required.[/red]")
            raise typer.Exit(1)

    if backend_type == BackendType.LAUNCHFLOW:
        login_or_signup = False
        if config.credentials is None:
            console.print("[yellow]No LaunchFlow Cloud credentials found.[/yellow]")
            login_or_signup = beaupy.confirm(
                "Would you like to login / sign up for LaunchFlow Cloud? It's free!",
                default_is_yes=True,
            )
            console.print(
                "Would you like to login / sign up for LaunchFlow Cloud? It's free!"
            )
            if not login_or_signup:
                console.print("[pink1]>[/pink1] No")
                backend_type = BackendType.LOCAL
                console.print(
                    "\n[italic]Switching to [bold]local[/bold] backend.[/italic]"
                )
            else:
                console.print("[pink1]>[/pink1] Yes")
        else:
            # NOTE: We only try to refresh creds if the user is already logged in.
            try:
                config.get_access_token()
            except exceptions.LaunchFlowRequestFailure:
                console.print("[red]Failed to refresh LaunchFlow credentials.[/red]")
                login_or_signup = beaupy.confirm(
                    "Would you like to re-login to LaunchFlow?",
                    default_is_yes=True,
                )
                console.print("Would you like to re-login to LaunchFlow?")
                if not login_or_signup:
                    console.print("[pink1]>[/pink1] No")
                    backend_type = BackendType.LOCAL
                    console.print(
                        "\n[italic]Switching to [bold]local[/bold] backend.[/italic]"
                    )
                else:
                    console.print("[pink1]>[/pink1] Yes")
            except exceptions.NoLaunchFlowCredentials:
                console.print("[red]No LaunchFlow credentials found.[/red]")
                login_or_signup = beaupy.confirm(
                    "Would you like to login / sign up for LaunchFlow? It's free!",
                    default_is_yes=True,
                )
                console.print(
                    "Would you like to login / sign up for LaunchFlow? It's free!"
                )
                if not login_or_signup:
                    console.print("[pink1]>[/pink1] No")
                    backend_type = BackendType.LOCAL
                    console.print(
                        "\n[italic]Switching to [bold]local[/bold] backend.[/italic]"
                    )
                else:
                    console.print("[pink1]>[/pink1] Yes")

        if login_or_signup:
            async with async_launchflow_client_ctx(None) as client:
                await login_flow(client)

        async with async_launchflow_client_ctx(None) as client:
            accounts = await client.accounts.list()
            if len(accounts) == 0:
                console.print("[red]Failed to fetch LaunchFlow accounts.[/red]")
                console.print(
                    "Please contact team@launchflow.com if the issue persists.\n"
                )
                raise typer.Exit(1)
            elif len(accounts) > 1:
                console.print("Which LaunchFlow account would you like to use?")
                account_id = beaupy.select(
                    [account.id for account in accounts], strict=True
                )
                if account_id is None:
                    console.print("No account selected. Exiting.")
                    raise typer.Exit(1)
                console.print(f"[pink1]>[/pink1] {account_id}")
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
            console.print(
                "Would you like to migrate your local project state to LaunchFlow Cloud?"
            )
            if migrate_to_launchflow:
                console.print("[pink1]>[/pink1] Yes")
                await migrate(source=existing_backend, target=backend)
                console.print(
                    "[green]Project state successfully migrated to LaunchFlow Cloud.[/green]"
                )
                project_name = existing_project_name
            else:
                console.print("[pink1]>[/pink1] No")

        if not migrate_to_launchflow:
            async with async_launchflow_client_ctx(
                launchflow_account_id=account_id
            ) as client:
                project = await get_project(
                    client=client.projects,
                    account_id=account_id,
                    project_name=None,
                    prompt_for_creation=True,
                    custom_selection_prompt="Select a project to deploy to:",
                    console=console,
                )
                project_name = project.name

    if backend_type == BackendType.LOCAL:
        project_name = beaupy.prompt(
            "What would you like to name your LaunchFlow project?",
            initial_value=existing_project_name,
        )
        while True:
            try:
                validate_project_name(project_name)
                break
            except ValueError as e:
                reason = str(e)
                console.print(f"[red]{reason}[/red]")
                project_name = beaupy.prompt("Please enter a new project name.")
        console.print("What would you like to name your LaunchFlow project?")
        console.print(f"[pink1]>[/pink1] {project_name}\n")

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

    with open(config_path, "r") as config_file:
        contents = config_file.read()

    console.print("\n[green]✓ launchflow.yaml created[/green]\n")
    syntax = Syntax(
        f"""# launchflow.yaml
{contents.rstrip()}""",
        "yaml",
        padding=(1, 1, 1, 1),
    )
    console.print(syntax)
    console.print("")

    # Append to the gitignore (if .launchflow is not already in the gitignore)
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    maybe_append_file_to_gitignore(
        file_name=".launchflow", gitignore_path=gitignore_path
    )


class DeploymentType(Enum):
    SERVICE = "Service (API)"
    WEBSITE = "Website"
    # JOB = "Scheduled Job"
    # WORKER = "Worker"
    # SERVER = "Server"
    # AGENT = "AI Agent"


def _select_deployment() -> Optional[DeploymentType]:
    rich.print("What would you like to deploy?")
    options = [d.value for d in DeploymentType]
    answer = beaupy.select(options=options, return_index=True)
    if answer is None:
        typer.echo("No deployment selected. Exiting.")
        raise typer.Exit(1)
    rich.print(f"[pink1]>[/pink1] {options[answer]}\n")
    return DeploymentType(options[answer])


class CloudProvider(Enum):
    AWS = "AWS"
    GCP = "GCP"


def _select_cloud_provider() -> Optional[CloudProvider]:
    rich.print("Which cloud provider would you like to deploy to?")
    options = [cp.value for cp in CloudProvider]
    answer = beaupy.select(options=options, return_index=True)
    if answer is None:
        rich.print("[pink1]No cloud provider selected.[/pink1]")
        return None
    rich.print(f"[pink1]>[/pink1] {options[answer]}\n")
    return CloudProvider(options[answer])


class AWSServices(Enum):
    LAMBDA = "Lambda (Serverless)"
    ECS = "ECS Fargate (Autoscaling VMs)"
    # EKS = "EKS (Kubernetes)"

    def title(self):
        if self == AWSServices.LAMBDA:
            return "Lambda"
        elif self == AWSServices.ECS:
            return "ECS"
        # elif self == AWSServices.EKS:
        #     return "EKS"

    def infra_dot_py_code(self):
        if self == AWSServices.LAMBDA:
            return """
# LambdaService Docs: https://docs.launchflow.com/reference/aws-services/lambda-service
api = lf.aws.LambdaService("my-lambda-api", handler="TODO")
"""
        if self == AWSServices.ECS:
            return """
# ECSFargateService Docs: https://docs.launchflow.com/reference/aws-services/ecs-fargate
api = lf.aws.ECSFargateService(
    "my-ecs-api",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
"""


#         elif self == AWSServices.EKS:
#             return """
# # EKS Docs: https://docs.launchflow.com/reference/aws-services/eks
# cluster = lf.aws.EKSCluster("my-eks-cluster")
# service = lf.aws.EKSService("my-eks-service", cluster=cluster)
# """


class GCPServices(Enum):
    CLOUD_RUN = "Cloud Run (Serverless)"
    GCE = "Compute Engine (Autoscaling VMs)"
    GKE = "GKE (Kubernetes)"

    def title(self):
        if self == GCPServices.CLOUD_RUN:
            return "Cloud Run"
        elif self == GCPServices.GCE:
            return "Compute Engine"
        elif self == GCPServices.GKE:
            return "GKE"

    def infra_dot_py_code(self):
        if self == GCPServices.CLOUD_RUN:
            return """
# Cloud Run Docs: https://docs.launchflow.com/reference/gcp-services/cloud-run
api = lf.gcp.CloudRunService(
    "my-cloud-run-api",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
"""
        elif self == GCPServices.GCE:
            return """
# Compute Engine Docs: https://docs.launchflow.com/reference/gcp-services/compute-engine-service
api = lf.gcp.ComputeEngineService(
    "my-compute-engine-api",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
"""
        elif self == GCPServices.GKE:
            return """
# GKE Docs: https://docs.launchflow.com/reference/gcp-services/gke-service
cluster = lf.gcp.GKECluster("my-gke-cluster")
api = lf.gcp.GKEService(
    "my-gke-api",
    cluster=cluster,
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
"""


def _select_service(cloud_provider: CloudProvider) -> Union[AWSServices, GCPServices]:
    if cloud_provider == CloudProvider.AWS:
        rich.print("Which AWS service would you like to use?")
        options = [s.value for s in AWSServices]
        answer = beaupy.select(options=options, return_index=True)
        if answer is None:
            typer.echo("No AWS service selected. Exiting.")
            raise typer.Exit(1)
        rich.print(f"[pink1]>[/pink1] {options[answer]}")
        return AWSServices(options[answer])
    elif cloud_provider == CloudProvider.GCP:
        rich.print("Which GCP service would you like to use?")
        options = [s.value for s in GCPServices]
        answer = beaupy.select(options=options, return_index=True)
        if answer is None:
            typer.echo("No GCP service selected. Exiting.")
            raise typer.Exit(1)
        rich.print(f"[pink1]>[/pink1] {options[answer]}")
        return GCPServices(options[answer])


class AWSWebsites(Enum):
    S3 = "S3 (Static Website)"
    # EC2 = "EC2 + Nginx (Dynamic Website)"

    def infra_dot_py_code(self):
        return """
# S3 Static Website Docs: https://docs.launchflow.com/reference/aws-websites/s3
website = lf.aws.S3Website(
    name="my-static-website",
    bucket_name="my-static-website-bucket",
    index_html="index.html",
    error_html="error.html",
)
"""

    def title(self):
        return "S3"


class GCPWebsites(Enum):
    GCS = "GCS (Static Website)"
    # GCE = "GCE + Nginx (Dynamic Website)"

    def infra_dot_py_code(self):
        return """
# GCS Static Website Docs: https://docs.launchflow.com/reference/gcp-websites/gcs
website = lf.gcp.GCSWebsite(
    name="my-static-website",
    bucket_name="my-static-website-bucket",
    index_html="index.html",
    error_html="error.html",
)
"""

    def title(self):
        return "GCS"


def _select_website(cloud_provider: CloudProvider) -> Union[AWSWebsites, GCPWebsites]:
    if cloud_provider == CloudProvider.AWS:
        rich.print("Which AWS service would you like to use?")
        options = [s.value for s in AWSWebsites]
        answer = beaupy.select(options=options, return_index=True)
        if answer is None:
            typer.echo("No AWS service selected. Exiting.")
            raise typer.Exit(1)
        rich.print(f"[pink1]>[/pink1] {options[answer]}")
        return AWSWebsites(options[answer])
    elif cloud_provider == CloudProvider.GCP:
        rich.print("Which GCP service would you like to use?")
        options = [s.value for s in GCPWebsites]
        answer = beaupy.select(options=options, return_index=True)
        if answer is None:
            typer.echo("No GCP service selected. Exiting.")
            raise typer.Exit(1)
        rich.print(f"[pink1]>[/pink1] {options[answer]}")
        return GCPWebsites(options[answer])


def generate_infra_dot_py():
    infra_py_path = os.path.join(os.getcwd(), "infra.py")
    if os.path.isfile(infra_py_path):
        rich.print("[yellow]An infra.py file already exists.[/yellow]")
        rich.print("[italic]Skipping example infra.py creation.[/italic]")
        return

    answer = beaupy.confirm(
        "Would you like to create an example [bold]infra.py[/bold] file?",
        default_is_yes=True,
    )
    rich.print("Would you like to create an example [bold]infra.py[/bold] file?")
    if not answer:
        rich.print("[pink1]>[/pink1] No")
        return
    rich.print("[pink1]>[/pink1] Yes\n")

    # deployment_type = _select_deployment()
    deployment_type = DeploymentType.SERVICE
    cloud_provider = _select_cloud_provider()
    if cloud_provider is None:
        rich.print("\n[italic]Skipping [bold]infra.py[/bold] creation.[/italic]")
        return
    if deployment_type == DeploymentType.SERVICE:
        deployment_option = _select_service(cloud_provider)
    # elif deployment_type == DeploymentType.WEBSITE:
    #     deployment_option = _select_website(cloud_provider)

    with open(infra_py_path, "w") as infra_py_file:
        infra_py_file.write(
            f"""\"\"\"infra.py

This file is used to customize the infrastructure your application deploys to.

Create your cloud infrastructure with:
    lf create

Deploy your application with:
    lf deploy

\"\"\"

import launchflow as lf
{deployment_option.infra_dot_py_code()}"""
        )

    rich.print("\n[green]✓ infra.py created[/green]\n")

    with open(infra_py_path, "r") as infra_py_file:
        contents = infra_py_file.read()

    # Remove docstrings (""" or ''')
    contents = re.sub(
        r"\"\"\"(.*?)\"\"\"|\'\'\'(.*?)\'\'\'", "", contents, flags=re.DOTALL
    )

    # Remove single-line comments (#)
    contents = re.sub(r"#.*", "", contents)

    # Remove double newlines
    contents = re.sub(r"\n\n", "\n", contents)

    syntax = Syntax(
        f"""# infra.py
{contents.strip()}""",
        "python",
        padding=(1, 1, 1, 1),
    )
    rich.print(syntax)


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
