import logging
import os
import subprocess

import httpx

from launchflow import exceptions
from launchflow.config import config

TOFU_VERSION = "1.7.2"


def needs_opentofu():
    return not os.path.exists(config.env.tofu_path)


def install_opentofu():
    base_dir = os.path.dirname(config.env.tofu_path)
    os.makedirs(base_dir, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        response = client.get("https://get.opentofu.org/install-opentofu.sh")
        response.raise_for_status()
        install_script_path = os.path.join(base_dir, "install-opentofu.sh")
        with open(install_script_path, "w") as f:
            f.write(response.text)
        try:
            os.chmod(install_script_path, 0o755)
            # TODO: we should check if checksum is installed and if it is we can verify
            # NOTE: we pass: `--symlink-path -` to avoid creating a symlink this means
            # the command doesn't need to run as sudo
            process = subprocess.run(
                f"./install-opentofu.sh --install-method standalone --install-path {base_dir} --opentofu-version {TOFU_VERSION} --skip-verify --symlink-path -",
                cwd=base_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if process.returncode != 0:
                logging.error(process.stdout.decode())
                raise exceptions.OpenTofuInstallFailure()
            logging.debug(process.stdout.decode())
        finally:
            os.remove(install_script_path)
