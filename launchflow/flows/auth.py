import asyncio
import base64
import secrets
import webbrowser
from typing import Optional

import beaupy  # type: ignore
import requests
import rich
from rich.progress import Progress, SpinnerColumn, TextColumn

from launchflow.clients.client import LaunchFlowAsyncClient
from launchflow.config import config


def _generate_state(length=64):
    random_bytes = secrets.token_bytes(length)
    code_verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
    code_verifier = code_verifier.rstrip("=")
    return code_verifier


async def login_flow(client: LaunchFlowAsyncClient):
    state = _generate_state()
    response = requests.get(
        f"{config.get_launchflow_cloud_url()}/auth/login?state={state}"
    )
    if response.status_code == 200:
        authorize_url = response.json()["url"]
    else:
        raise RuntimeError(f"Failed to get auth url. {response.reason}")

    successful = webbrowser.open(authorize_url)
    if not successful:
        raise RuntimeError("Failed to open browser")

    # poll the server for the access token
    # NOTE: we print a new line to make the console output more balanced.
    print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Waiting for access token...", total=None)

        credentials = None
        while credentials is None:
            response = requests.get(
                f"{config.get_launchflow_cloud_url()}/auth/access_token?state={state}"
            )
            if response.status_code == 200:
                credentials = response.json()
            elif response.status_code != 202:  # 202 = still waiting
                raise RuntimeError(f"Failed to get access token. {response.reason}")
            else:
                await asyncio.sleep(3)

        config.update_credentials(credentials)
        accounts = await client.accounts.list()

        account_id: Optional[str] = None
        if not accounts:
            raise RuntimeError(
                "Account information not found. Please try again and contact founders@launchflow.com if the issue persists."
            )
        if len(accounts) == 1:
            account_id = accounts[0].id
        else:
            account_id = beaupy.select(
                "Select an account",
                [account.id for account in accounts],
                strict=True,
            )
            if account_id is None:
                raise RuntimeError("No account selected")

        progress.remove_task(task)
        progress.console.print("[green]✓[/green] Login successful")


def logout_flow():
    if config.credentials is None:
        print("Not logged in")
        return

    response = requests.post(
        f"{config.get_launchflow_cloud_url()}/auth/logout",
        json={"refresh_token": config.credentials.refresh_token},
    )
    if response.status_code == 401:
        config.clear_credentials()
        raise RuntimeError(
            "Local credentials cleared, but failed to invalidate refresh token on the server."
        )
    elif response.status_code != 200:
        raise RuntimeError(f"{response.reason}")

    config.clear_credentials()
    rich.print("[green]✓[/green] Logout successful")


def refresh_credentials_flow():
    if config.credentials is None:
        print("Not logged in")
        return

    response = requests.post(
        f"{config.get_launchflow_cloud_url()}/auth/refresh",
        json={"refresh_token": config.credentials.refresh_token},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to refresh credentials. {response.reason}")

    config.update_credentials(response.json())
    rich.print("[green]✓[/green] Credentials refreshed")


def me_flow():
    if config.credentials is None:
        print("Not logged in")
        return

    response = requests.get(
        f"{config.get_launchflow_cloud_url()}/auth/me",
        headers={"Authorization": f"Bearer {config.get_access_token()}"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to get user info. {response.reason}")

    rich.print(response.json())
