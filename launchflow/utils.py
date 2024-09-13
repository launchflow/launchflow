import contextlib
import logging
import logging.handlers
import os
import secrets
import string
import sys
import time
import traceback
from io import IOBase
from typing import IO, Optional, Union

import httpx
from requests import Response

from launchflow.logger import logger


# TODO: Move "potential fix" messsages into the server.
# Server should return a json payload with a message per client type, i.e.
# {status: 409, message: "Conflict...", fix: {"cli": "Run this command..."}}
# Use details to return the fix payload:
# details = {message: "...", fix: {"cli": "Run this command..."}}
def get_failure_text(response: Union[httpx.Response, Response]) -> str:
    status_code = response.status_code
    try:
        json_response = response.json()
        return f"({status_code}): {json_response['detail']}"
    except Exception:
        if isinstance(response, Response):
            return f"({status_code}): {response.reason}"
        return f"({status_code}): {response.reason_phrase}"


def generate_random_password(
    length: int = 12, include_special_chars: bool = False
) -> str:
    """
    Generates a random password using the secrets module.
    ref: https://www.educative.io/answers/what-is-the-secretschoice-function-in-python

    **Args:**
    - `length` (int): The length of the password to generate.
    - `include_special_chars` (bool): Whether to include special characters in the password.

    **Returns:**
    - A random password string.
    """
    characters = string.ascii_letters + string.digits
    if include_special_chars:
        characters += string.punctuation

    password = "".join(secrets.choice(characters) for _ in range(length))
    return password


# TODO: explore other ways to generate / set a deployment_id
def generate_deployment_id() -> str:
    """
    Generates a random deployment ID using the current time in milliseconds.

    **Returns:**
    - A deployment ID string.
    """
    time_millis = int(time.time() * 1000)
    return str(time_millis)


@contextlib.contextmanager
def logging_output(filename: Optional[str], drop_logs: bool = False):
    """Context manager to log output to a file."""
    if drop_logs:
        fh = open(os.devnull, "w")
    elif filename is not None:
        # NOTE: We use "a" mode here so we append to the log file if it already exists
        fh = open(filename, "a")
    else:
        fh = sys.stdout  # type: ignore

    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()


@contextlib.contextmanager
def redirect_stdout_stderr(fh: IOBase):
    """Context manager to redirect stdout and stderr to a file-like object."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_handlers = logging.root.handlers[:]

    sys.stdout = fh
    sys.stderr = fh
    logging.root.handlers = [logging.StreamHandler(fh)]

    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        logging.root.handlers = old_handlers


def dump_exception_with_stacktrace(e: Exception, file: IO):
    file.write("Exception occurred:\n")
    file.write(f"Type: {type(e).__name__}\n")
    file.write(f"Message: {str(e)}\n")
    file.write("Stacktrace:\n")
    file.write(traceback.format_exc())
    file.write("\n\n")

    # Log the exception to the logger
    logger.debug(
        "Exception occurred.\nException: %s",
        e,
        exc_info=True,
    )
