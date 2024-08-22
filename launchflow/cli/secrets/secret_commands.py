import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

import launchflow
from launchflow.aws.secrets_manager import SecretsManagerSecret
from launchflow.cli.constants import ENVIRONMENT_HELP
from launchflow.cli.utyper import UTyper
from launchflow.config import config
from launchflow.gcp.secret_manager import SecretManagerSecret
from launchflow.managers.resource_manager import ResourceManager
from launchflow.models.enums import ResourceProduct

app = UTyper(help="Commands for managing secrets in LaunchFlow")


@app.command()
async def set(
    resource_name: str = typer.Argument(..., help="Resource to fetch information for."),
    secret_value: str = typer.Argument(..., help="The value to set for the secret."),
    environment: str = typer.Option(..., help=ENVIRONMENT_HELP),
):
    """Set the value of a secret managed by LaunchFlow."""
    # TODO: Make environment nullable and add a selection prompt if not provided
    launchflow.environment = environment

    rm = ResourceManager(
        project_name=launchflow.project,
        environment_name=environment,
        backend=config.launchflow_yaml.backend,
        resource_name=resource_name,
    )
    resource = await rm.load_resource()
    if resource.product == ResourceProduct.GCP_SECRET_MANAGER_SECRET.value:

        async def add_version_fn():
            secret = SecretManagerSecret(name=resource_name)
            secret.add_version(secret_value.encode("utf-8"))

    elif resource.product == ResourceProduct.AWS_SECRETS_MANAGER_SECRET.value:

        async def add_version_fn():
            secret = SecretsManagerSecret(name=resource_name)
            secret.add_version(secret_value)

    else:
        typer.echo(
            "Only secrets managed by Google Cloud Secret Manager and AWS Secrets Manager are supported."
        )
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn("["),
        TimeElapsedColumn(),
        TextColumn("]"),
    ) as progress:
        task = progress.add_task(
            f"Setting secret value for {resource_name}...",
        )
        await add_version_fn()
        progress.remove_task(task)
        progress.console.print("[green]✓[/green] Successfully added secret value")
