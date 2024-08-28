import os
import subprocess

import httpx

from launchflow import exceptions
from launchflow.logger import logger

BASE_BIN_DIR = os.path.join(os.path.expanduser("~"), ".launchflow", "bin")
TOFU_PATH = os.path.join(BASE_BIN_DIR, "tofu")
TOFU_VERSION = "1.7.2"


if os.name == "nt":
    remote_path = "https://get.opentofu.org/install-opentofu.ps1"
    install_cmd = f"powershell.exe -ExecutionPolicy Bypass -File .\\install-opentofu.ps1 -installMethod standalone -installPath {BASE_BIN_DIR} -opentofuVersion {TOFU_VERSION} -skipVerify"
    install_script_path = os.path.join(BASE_BIN_DIR, "install-opentofu.ps1")
else:
    remote_path = "https://get.opentofu.org/install-opentofu.sh"
    # TODO: we should check if checksum is installed and if it is we can verify
    # NOTE: we pass: `--symlink-path -` to avoid creating a symlink this means
    # the command doesn't need to run as sudo
    install_cmd = f"./install-opentofu.sh --install-method standalone --install-path {BASE_BIN_DIR} --opentofu-version {TOFU_VERSION} --skip-verify --symlink-path -"
    install_script_path = os.path.join(BASE_BIN_DIR, "install-opentofu.sh")


def needs_opentofu():
    return not os.path.exists(os.path.join(BASE_BIN_DIR, "tofu"))


def install_opentofu():
    os.makedirs(BASE_BIN_DIR, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        response = client.get(remote_path)
        response.raise_for_status()
        with open(install_script_path, "w") as f:
            if os.name == "nt":
                f.write(
                    "Import-Module $PSHOME\\Modules\\Microsoft.PowerShell.Utility -Function Get-FileHash\n"
                )
            f.write(response.text)
        try:
            logger.debug(f"Running install script: {install_cmd}")
            os.chmod(install_script_path, 0o755)
            process = subprocess.run(
                install_cmd,
                cwd=BASE_BIN_DIR,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if process.returncode != 0:
                logger.error(process.stdout.decode())
                raise exceptions.OpenTofuInstallFailure()
            logger.debug(process.stdout.decode())
        finally:
            os.remove(install_script_path)
