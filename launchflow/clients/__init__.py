import contextlib
from typing import Optional

from launchflow.config import config

from .client import LaunchFlowAsyncClient


# TODO: this should probably get the account id from the config
@contextlib.asynccontextmanager
async def async_launchflow_client_ctx(
    launchflow_account_id: Optional[str],
    base_url: Optional[str] = None,
):
    if base_url is None:
        base_url = config.get_launchflow_cloud_url()
    launchflow_async_client = LaunchFlowAsyncClient(
        base_url,
        launchflow_account_id=launchflow_account_id,  # type: ignore
    )
    try:
        yield launchflow_async_client
    finally:
        await launchflow_async_client.close()
