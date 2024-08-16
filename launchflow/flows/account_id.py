from typing import Optional

import beaupy  # type: ignore
import rich
from rich.progress import Progress, SpinnerColumn, TextColumn

from launchflow.clients.client import LaunchFlowAsyncClient


async def list_account_ids_remote(
    client: LaunchFlowAsyncClient, account_id: Optional[str]
) -> str:
    if account_id is None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Fetching accounts...", total=None)
            accounts = await client.accounts.list()
            progress.remove_task(task)
        account_ids = [f"{a.id}" for a in accounts]
        selected_account = beaupy.select(account_ids, return_index=True, strict=True)
        account_id = account_ids[selected_account]
        rich.print(f"[pink1]>[/pink1] {account_id}")
    return account_id
