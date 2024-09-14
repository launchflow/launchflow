import datetime
import logging
import os
import time
from typing import Optional, Tuple

import beaupy  # type: ignore
import httpx
import rich
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from launchflow import exceptions
from launchflow.backend import LaunchFlowBackend
from launchflow.clients.projects_client import ProjectsAsyncClient
from launchflow.config import config
from launchflow.flows.project_flows import create_project
from launchflow.locks import LockOperation, OperationType
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.project_manager import ProjectManager
from launchflow.models.enums import CloudProvider, EnvironmentStatus, EnvironmentType
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
)
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.validation import validate_environment_name
from launchflow.workflows import (
    AWSEnvironmentCreationInputs,
    AWSEnvironmentDeletionInputs,
    GCPEnvironmentCreationInputs,
    GCPEnvironmentDeletionInputs,
    create_aws_environment,
    create_gcp_environment,
    delete_aws_environment,
    delete_gcp_environment,
)

_GCP_REGIONS = [
    "us-central1",  # Iowa, USA
    "us-east1",  # South Carolina, USA
    "us-east4",  # Northern Virginia, USA
    "us-west1",  # Oregon, USA
    "us-west2",  # Los Angeles, California, USA
    "us-west3",  # Salt Lake City, Utah, USA
    "us-west4",  # Las Vegas, Nevada, USA
    "northamerica-northeast1",  # Montréal, Canada
    "southamerica-east1",  # São Paulo, Brazil
    "europe-west1",  # Belgium
    "europe-west2",  # London, UK
    "europe-west3",  # Frankfurt, Germany
    "europe-west4",  # Netherlands
    "europe-west6",  # Zürich, Switzerland
    "europe-north1",  # Finland
    "asia-east1",  # Taiwan
    "asia-east2",  # Hong Kong
    "asia-northeast1",  # Tokyo, Japan
    "asia-northeast2",  # Osaka, Japan
    "asia-northeast3",  # Seoul, South Korea
    "asia-southeast1",  # Singapore
    "asia-southeast2",  # Jakarta, Indonesia
    "australia-southeast1",  # Sydney, Australia
    "australia-southeast2",  # Melbourne, Australia
]


async def get_environment(
    project_state_manager: ProjectManager,
    environment_name: Optional[str] = None,
    prompt_for_creation: bool = True,
    allow_failed: bool = False,
) -> Tuple[str, EnvironmentState]:
    if environment_name is None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Fetching environments...", total=None)
            environments = await project_state_manager.list_environments()
            progress.remove_task(task)
        ready_environments = []
        pending_environments = []
        failed_environments = []
        for name, env in environments.items():
            if env.status.is_pending():
                pending_environments.append(name)
            elif env.status == EnvironmentStatus.READY or allow_failed:
                ready_environments.append(name)
            else:
                failed_environments.append(name)

        if failed_environments and not allow_failed:
            for name in failed_environments:
                rich.print(
                    f"[red]✗[/red] Environment `{name}` is in a failed state and cannot be used."
                )
            rich.print(
                "You can try re-creating failed environments with `lf environments create {env name}`."
            )
            print()
        if pending_environments:
            for name in pending_environments:
                rich.print(
                    f"[yellow]⚠[/yellow]  Environment `{name}` is in a pending state and cannot be used."
                )
            rich.print(
                "You can check the status of pending environments with `lf environments list`."
            )
            print()

        if prompt_for_creation:
            ready_environments.append("[i yellow]Create new environment[/i yellow]")
        if len(ready_environments) == 0:
            raise exceptions.NoEnvironmentsFoundError()
        print("Select the environment to use:")
        selected_environment = beaupy.select(ready_environments, strict=True)
        if selected_environment is None:
            rich.print("[red]No environment selected.")
            raise typer.Exit(1)
        if prompt_for_creation and selected_environment == ready_environments[-1]:
            if environment_name is None:
                environment_name = beaupy.prompt("Enter the environment name:")
                rich.print(f"[pink1]>[/pink1] {environment_name}\n")
            validate_environment_name(environment_name)
            environment = await create_environment(
                environment_type=None,
                cloud_provider=None,
                manager=EnvironmentManager(
                    project_name=project_state_manager.project_name,
                    environment_name=environment_name,
                    backend=project_state_manager.backend,
                ),
            )
            if environment is None:
                raise exceptions.EnvironmentCreationFailed(environment_name)
        else:
            rich.print(f"[pink1]>[/pink1] {selected_environment}")
            print()
            environment = environments[selected_environment]
            environment_name = selected_environment
        return environment_name, environment
    try:
        # Fetch the environment to ensure it exists
        env_manager = EnvironmentManager(
            project_name=project_state_manager.project_name,
            environment_name=environment_name,
            backend=project_state_manager.backend,
        )
        environment = await env_manager.load_environment()
    except exceptions.EnvironmentNotFound as e:
        if prompt_for_creation:
            answer = beaupy.confirm(
                f"Environment `{environment_name}` does not exist yet. Would you like to create it?"
            )
            if answer:
                environment = await create_environment(
                    environment_type=None,
                    cloud_provider=None,
                    manager=EnvironmentManager(
                        project_name=project_state_manager.project_name,
                        environment_name=environment_name,
                        backend=project_state_manager.backend,
                    ),
                )
                if environment is None:
                    raise exceptions.EnvironmentCreationFailed(environment_name)
            else:
                raise e
        else:
            raise e
    return environment_name, environment


async def delete_environment(
    manager: EnvironmentManager, detach: bool = False, prompt: bool = True
):
    if prompt:
        user_confirmation = beaupy.confirm(
            f"Would you like to delete the environment `{manager.environment_name}`?",
        )
        if not user_confirmation:
            rich.print("[red]✗[/red] Environment deletion canceled.")
            return

    launchflow_uri = LaunchFlowURI(
        environment_name=manager.environment_name, project_name=manager.project_name
    )
    async with await manager.lock_environment(
        operation=LockOperation(operation_type=OperationType.DELETE_ENVIRONMENT)
    ) as lock:
        existing_environment = await manager.load_environment()
        existing_resources = await manager.list_resources()
        existing_services = await manager.list_services()
        if not detach:
            if existing_resources or existing_services:
                raise exceptions.EnvironmentNotEmpty(manager.environment_name)

            try:
                if existing_environment.gcp_config is not None:
                    await delete_gcp_environment(
                        inputs=GCPEnvironmentDeletionInputs(
                            launchflow_uri=launchflow_uri,
                            environment_state=existing_environment,
                        )
                    )
                elif existing_environment.aws_config is not None:
                    base_logging_dir = "/tmp/launchflow"
                    os.makedirs(base_logging_dir, exist_ok=True)
                    logs_file = f"{base_logging_dir}/delete-aws-environment-{manager.environment_name}-{int(time.time())}.log"
                    rich.print(f"Logging to [pink1]{logs_file}[/pink1]")

                    await delete_aws_environment(
                        inputs=AWSEnvironmentDeletionInputs(
                            launchflow_uri=launchflow_uri,
                            aws_region=existing_environment.aws_config.region,
                            artifact_bucket=existing_environment.aws_config.artifact_bucket,
                            lock_id=lock.lock_id,
                            logs_file=logs_file,
                        )
                    )
            except Exception as e:
                logging.debug("Exception occurred: %s", e, exc_info=True)
                existing_environment.status = EnvironmentStatus.DELETE_FAILED
                await manager.save_environment(existing_environment, lock.lock_id)
                raise e

        # Note: environment deletion cascades so all resource and service states are deleted
        await manager.delete_environment(lock.lock_id)
        rich.print("[green]✓[/green] Environment deleted.")


async def lookup_organization(prompt: bool = True):
    try:
        from google.cloud import resourcemanager_v3
    except ImportError:
        raise exceptions.MissingGCPDependency()
    organization_client = resourcemanager_v3.OrganizationsAsyncClient()

    orgs = await organization_client.search_organizations()
    org: Optional[resourcemanager_v3.Organization] = None
    # 1. look up organiztaion for the project
    # We do this first to ensure it won't fail before creating the project
    all_orgs = []
    async for o in orgs:
        all_orgs.append(o)
    if not all_orgs:
        raise exceptions.NoOrgs()
    if len(all_orgs) > 1:
        if not prompt:
            raise ValueError(
                "Multiple organizations found. Please provide one with the --gcp-org flag or run interactively."
            )
        print(
            "You have access to multiple organizations. Please select which one to use:"
        )
        org_options = [f"{o.display_name} ({o.name})" for o in all_orgs]
        org_idx = beaupy.select(org_options, return_index=True, strict=True)
        if org_idx is None:
            raise ValueError("No org selected")
        org = all_orgs[org_idx]
        rich.print(f"[pink1]>[/pink1] {org_options[org_idx]}")
        print()

    else:
        org = all_orgs[0]
    return org.name  # type: ignore


async def create_environment(
    environment_type: Optional[EnvironmentType],
    cloud_provider: Optional[CloudProvider],
    manager: EnvironmentManager,
    # GCP cloud provider options, this are used if you are importing an existing setup
    gcp_project_id: Optional[str] = None,
    gcs_artifact_bucket: Optional[str] = None,
    gcp_organization_name: Optional[str] = None,
    environment_service_account_email: Optional[str] = None,
    prompt: bool = True,
) -> Optional[EnvironmentState]:
    """Create a new environment in a project."""
    if isinstance(manager.backend, LaunchFlowBackend):
        # If we're using the launchflow backend verify that the project exists
        async with httpx.AsyncClient(timeout=60) as client:
            proj_client = ProjectsAsyncClient(
                client,
                manager.backend.lf_cloud_url,
                config.get_account_id(),
            )
            try:
                _ = await proj_client.get(manager.project_name)
            except exceptions.ProjectNotFound:
                rich.print(
                    f"[red]✗[/red] Project `{manager.project_name}` does not exist."
                )
                if prompt:
                    project = await create_project(
                        proj_client,
                        manager.project_name,
                        config.get_account_id(),
                    )
                    if project is None:
                        raise
                    print()
                else:
                    raise
    async with await manager.lock_environment(
        operation=LockOperation(operation_type=OperationType.CREATE_ENVIRONMENT)
    ) as lock:
        # TODO: maybe prompt the user if the environment already exists that this will update stuff
        try:
            existing_environment: Optional[
                EnvironmentState
            ] = await manager.load_environment()
        except exceptions.EnvironmentNotFound:
            existing_environment = None
        if (
            existing_environment is not None
            and existing_environment.status != EnvironmentStatus.UNKNOWN
        ):
            existing_environment_type = existing_environment.environment_type
            if (
                environment_type is not None
                and environment_type != existing_environment_type
            ):
                raise exceptions.ExistingEnvironmentDifferentEnvironmentType(
                    manager.environment_name, existing_environment_type
                )
            environment_type = existing_environment_type

            existing_cloud_provider = None
            if existing_environment.aws_config is not None:
                existing_cloud_provider = CloudProvider.AWS
            elif existing_environment.gcp_config is not None:
                existing_cloud_provider = CloudProvider.GCP
            else:
                raise ValueError("Environment has no cloud provider.")
            if cloud_provider is not None and cloud_provider != existing_cloud_provider:
                raise exceptions.ExistingEnvironmentDifferentCloudProvider(
                    manager.environment_name
                )

            cloud_provider = existing_cloud_provider

            # TODO: add tests for these exceptions being thrown
            if existing_environment.gcp_config is not None:
                if (
                    gcp_project_id is not None
                    and existing_environment.gcp_config.project_id is not None
                    and gcp_project_id != existing_environment.gcp_config.project_id
                ):
                    raise exceptions.ExistingEnvironmentDifferentGCPProject(
                        manager.environment_name,
                    )
                gcp_project_id = (
                    existing_environment.gcp_config.project_id or gcp_project_id
                )
                if (
                    gcs_artifact_bucket is not None
                    and existing_environment.gcp_config.artifact_bucket is not None
                    and gcs_artifact_bucket
                    != existing_environment.gcp_config.artifact_bucket
                ):
                    raise exceptions.ExistingEnvironmentDifferentGCPBucket(
                        manager.environment_name,
                    )
                gcs_artifact_bucket = (
                    existing_environment.gcp_config.artifact_bucket
                    or gcs_artifact_bucket
                )
                if (
                    environment_service_account_email is not None
                    and existing_environment.gcp_config.service_account_email
                    is not None
                    and environment_service_account_email
                    != existing_environment.gcp_config.service_account_email
                ):
                    raise exceptions.ExistingEnvironmentDifferentGCPServiceAccount(
                        manager.environment_name,
                    )
                environment_service_account_email = (
                    existing_environment.gcp_config.service_account_email
                    or environment_service_account_email
                )

        if environment_type is None and prompt:
            print("Select the environment type:")
            selection = beaupy.select(
                ["development", "production"],
                strict=True,
            )
            rich.print(f"[pink1]>[/pink1] {selection}")
            environment_type = EnvironmentType(selection)
            print()

        # TODO: move this logic into an EnvironmentPlan step
        if cloud_provider is None and prompt:
            print("Select the cloud provider for the environment:")
            selection = beaupy.select(["GCP", "AWS"], strict=True)
            rich.print(f"[pink1]>[/pink1] {selection}")
            cloud_provider = CloudProvider[selection]
            print()

        if cloud_provider is None:
            raise ValueError("Cloud provider is required.")

        if environment_type is None:
            raise ValueError("Environment type is required.")

        launchflow_uri = LaunchFlowURI(
            environment_name=manager.environment_name,
            project_name=manager.project_name,
        )

        base_logging_dir = "/tmp/launchflow"
        os.makedirs(base_logging_dir, exist_ok=True)
        logs_file = f"{base_logging_dir}/create-environment-{manager.environment_name}-{int(time.time())}.log"
        rich.print(f"Logging to [pink1]{logs_file}[/pink1]")

        if cloud_provider == CloudProvider.GCP:
            org_name = gcp_organization_name
            if gcp_project_id is None and org_name is None:
                org_name = await lookup_organization(prompt)

            if prompt:
                rich.print("Select the default region for the environment:")
                selected_region: Optional[str] = beaupy.select(
                    _GCP_REGIONS, strict=True, pagination=True
                )
                if selected_region is None:
                    typer.echo("No region selected - Exiting.")
                    raise typer.Exit(1)
                rich.print(f"[pink1]>[/pink1] {selected_region}\n")
            else:
                selected_region = "us-central1"

            vpc_connection_managed = None
            if (
                existing_environment is not None
                and existing_environment.gcp_config is not None
            ):
                vpc_connection_managed = (
                    existing_environment.gcp_config.vpc_connection_managed
                )
            gcp_environment_info = await create_gcp_environment(
                inputs=GCPEnvironmentCreationInputs(
                    launchflow_uri=launchflow_uri,
                    gcp_project_id=gcp_project_id,
                    environment_service_account_email=environment_service_account_email,
                    artifact_bucket=gcs_artifact_bucket,
                    org_name=org_name,
                    lock_id=lock.lock_id,
                    logs_file=logs_file,
                    vpc_connection_managed=vpc_connection_managed,
                ),
                prompt=prompt,
            )
            create_time = datetime.datetime.now(datetime.timezone.utc)
            status = (
                EnvironmentStatus.READY
                if gcp_environment_info.success
                else EnvironmentStatus.CREATE_FAILED
            )

            env = EnvironmentState(
                created_at=create_time,
                updated_at=create_time,
                gcp_config=GCPEnvironmentConfig(
                    project_id=gcp_environment_info.gcp_project_id,
                    default_region=selected_region,
                    default_zone=f"{selected_region}-a",
                    service_account_email=gcp_environment_info.environment_service_account_email,
                    artifact_bucket=gcp_environment_info.artifact_bucket,
                    vpc_connection_managed=gcp_environment_info.vpc_connection_managed,
                ),
                environment_type=environment_type,
                status=status,
            )
        elif cloud_provider == CloudProvider.AWS:
            if (
                existing_environment is not None
                and existing_environment.aws_config is not None
            ):
                aws_account_id = existing_environment.aws_config.account_id  # type: ignore
                region = existing_environment.aws_config.region  # type: ignore
            else:
                try:
                    import boto3
                    import botocore
                except ImportError:
                    raise exceptions.MissingAWSDependency()
                sts = boto3.client("sts")
                try:
                    response = sts.get_caller_identity()
                    aws_account_id = response["Account"]
                except botocore.exceptions.NoCredentialsError as e:
                    raise exceptions.NoAWSCredentialsFound() from e

                session = boto3.session.Session()
                region = session.region_name

                if prompt:
                    # TODO: Explore the idea of an "EnvironmentPlan" and move this prompt into the plan step
                    answer = beaupy.confirm(
                        f"Based on your credentials this will create an environment in AWS account {aws_account_id}. Would you like to continue?"
                    )
                    if not answer:
                        typer.echo("AWS account ID rejected - Exiting.")
                        raise typer.Exit(1)

                    # The messy founder code below sorts the regions relative to the user's default region.
                    # Its sorts in this order: default region, nearest regions, related country regions, other regions.
                    # For example, if the default region is us-west-2, the regions will be sorted as:
                    # us-west-2, us-west-1, us-east-1, us-east-2, af-south-1, ap-east-1, ...
                    all_regions = session.get_available_regions("ec2")

                    if region is None:
                        region = "us-east-1"

                    default_country, default_location, _ = region.split("-")

                    def sort_func(r: str) -> Tuple[int, str]:
                        # First sort by default region
                        if r == region:
                            return (0, r)
                        # Then sort by nearest regions
                        if r.startswith(f"{default_country}-{default_location}"):
                            return (1, r)
                        # Then sort by related country regions
                        if r.startswith(f"{default_country}-"):
                            return (2, r)
                        # Finally sort by other regions
                        return (3, r)

                    sorted_regions = sorted(all_regions, key=sort_func)

                    select_options = sorted_regions.copy()
                    select_options[0] = f"{select_options[0]} (default)"

                    print("Select the default region for the environment:")
                    region_index: Optional[int] = beaupy.select(
                        select_options, strict=True, pagination=True, return_index=True
                    )
                    if region_index is None:
                        typer.echo("No region selected - Exiting.")
                        raise typer.Exit(1)
                    region = sorted_regions[region_index]
                    rich.print(f"[pink1]>[/pink1] {region}")
                elif region is None:
                    raise exceptions.NoAWSRegionEvironmentCreationError()

            aws_environment_info = await create_aws_environment(
                inputs=AWSEnvironmentCreationInputs(
                    launchflow_uri=launchflow_uri,
                    region=region,
                    aws_account_id=aws_account_id,
                    environment_type=environment_type,
                    artifact_bucket=(
                        existing_environment.aws_config.artifact_bucket  # type: ignore
                        if existing_environment and existing_environment.aws_config
                        else None
                    ),
                    lock_id=lock.lock_id,
                    logs_file=logs_file,
                )
            )
            create_time = datetime.datetime.now(datetime.timezone.utc)
            status = (
                EnvironmentStatus.READY
                if aws_environment_info.success
                else EnvironmentStatus.CREATE_FAILED
            )
            env = EnvironmentState(
                created_at=create_time,
                updated_at=create_time,
                aws_config=AWSEnvironmentConfig(
                    artifact_bucket=aws_environment_info.artifact_bucket,
                    vpc_id=aws_environment_info.vpc_id,
                    iam_role_arn=aws_environment_info.role_arn,
                    region=region,
                    account_id=aws_account_id,
                ),
                environment_type=environment_type,
                status=status,
            )
        else:
            raise ValueError("Invalid cloud provider.")
        await manager.save_environment(env, lock.lock_id)

        if env.status == EnvironmentStatus.READY:
            rich.print("[green]Environment created successfully![/green]")
        else:
            rich.print(
                f"[red]✗ Failed to create environment.[/red] Logs: [pink1]{logs_file}[/pink1]"
            )
            rich.print(
                f"\n[yellow]NOTE[/yellow] You can run [blue]`lf environments create {manager.environment_name}`[/blue] to continue creation from where it left off."
            )
            rich.print(
                f"If the error persists, run [blue]`lf environments delete {manager.environment_name}`[/blue] to clean up the failed environment.\n"
            )
            return None

    return env
