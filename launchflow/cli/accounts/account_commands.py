import httpx
import typer

from launchflow.cli.utils import print_response
from launchflow.cli.utyper import UTyper
from launchflow.clients.accounts_client import AccountsAsyncClient
from launchflow.exceptions import LaunchFlowRequestFailure

app = UTyper(help="Commands for managing accounts in LaunchFlow")


@app.command()
async def get(
    account_id: str = typer.Argument("The account ID to fetch. Format: `account_123`"),
):
    """Get information about a specific account."""
    # TODO: this isn't right but it works for now
    async with httpx.AsyncClient(timeout=60) as http_client:
        client = AccountsAsyncClient(http_client=http_client)
        try:
            acc = await client.get(account_id)
            print_response("Account", acc.model_dump())
        except LaunchFlowRequestFailure as e:
            e.pretty_print()
            raise typer.Exit(1)


@app.command()
async def list():
    """List accounts that you have access to."""

    # TODO: this isn't right but it works for now
    async with httpx.AsyncClient(timeout=60) as http_client:
        client = AccountsAsyncClient(http_client=http_client)
        try:
            accounts = await client.list()
            print_response(
                "Accounts",
                {
                    "accounts": [acc.model_dump() for acc in accounts],
                },
            )
        except LaunchFlowRequestFailure as e:
            e.pretty_print()
            raise typer.Exit(1)
