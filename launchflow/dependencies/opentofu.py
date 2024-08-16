import logging
import os
import subprocess

import httpx

from launchflow import exceptions

BASE_BIN_DIR = os.path.join(os.path.expanduser("~"), ".launchflow", "bin")
TOFU_PATH = os.path.join(BASE_BIN_DIR, "tofu")
TOFU_VERSION = "1.7.2"


def needs_opentofu():
    return not os.path.exists(os.path.join(BASE_BIN_DIR, "tofu"))


def install_opentofu():
    os.makedirs(BASE_BIN_DIR, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        response = client.get("https://get.opentofu.org/install-opentofu.sh")
        response.raise_for_status()
        install_script_path = os.path.join(BASE_BIN_DIR, "install-opentofu.sh")
        with open(install_script_path, "w") as f:
            f.write(response.text)
        try:
            os.chmod(install_script_path, 0o755)
            # TODO: we should check if checksum is installed and if it is we can verify
            # NOTE: we pass: `--symlink-path -` to avoid creating a symlink this means
            # the command doesn't need to run as sudo
            process = subprocess.run(
                f"./install-opentofu.sh --install-method standalone --install-path {BASE_BIN_DIR} --opentofu-version {TOFU_VERSION} --skip-verify --symlink-path -",
                cwd=BASE_BIN_DIR,
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
