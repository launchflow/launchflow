import logging

import jwt
from posthog import Posthog

from launchflow import lf_config
from launchflow.version import __version__

# NOTE: We do not have any retries since this is best effort usage statistics.
# If the user doesnt' have an internect connection we don't want things to fail
# or to have noisy logs.
posthog = Posthog("phc_Df3dveOW6gG1ERjM1TQ8qBp7BRwEvLCjiB2FPUJPSwj", max_retries=0)
posthog_logger = logging.getLogger("posthog")
posthog_logger.setLevel(logging.CRITICAL)
backoff_logger = logging.getLogger("backoff")
backoff_logger.setLevel(logging.CRITICAL)

disable: bool = False


def _posthog_distinct_id():
    try:
        access_token = lf_config.get_access_token()
        payload = jwt.decode(access_token, options={"verify_signature": False})
        return payload["email"]
    except Exception:
        try:
            return lf_config.session.session_id
        except Exception:
            # TODO: we should probably rewrite the file or something but seems like an edge
            # case that is not worth the effort.
            return "unknown"


def record_cli_command(cli_action: str, success: bool):
    # First we try to identify the user with their email if the user
    # is using LaunchFlow Cloud.
    # If that fails we identify them with a uuid associated with their session
    if disable:
        return
    cli_command = " ".join(cli_action.split("_")[1:])
    distinct_id = _posthog_distinct_id()
    posthog.capture(
        distinct_id,
        f"cli_{cli_action}",
        {"version": __version__, "command": cli_command, "success": success},
    )


def record_cli_unexpected_error(error_type: str):
    if disable:
        return
    distinct_id = _posthog_distinct_id()
    posthog.capture(
        distinct_id,
        "cli_unexpected_error",
        {"version": __version__, "error_type": error_type},
    )
