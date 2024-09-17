import dataclasses
import logging
import os
import time
from typing import Any, Dict, Optional

import jwt
import requests
import toml

from launchflow import exceptions
from launchflow.backend import BackendOptions, LaunchFlowBackend
from launchflow.config.launchflow_env import LaunchFlowEnvVars, load_launchflow_env
from launchflow.config.launchflow_session import LaunchFlowSession
from launchflow.config.launchflow_yaml import (
    LaunchFlowDotYaml,
    load_launchflow_dot_yaml,
)

CREDENTIALS_PATH = os.path.expanduser("~/.config/launchflow/credentials.toml")
_REFRESH_BUFFER = 60  # seconds


def _decode_jwt(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        logging.debug(f"Error decoding JWT token: {e}")
        return None


@dataclasses.dataclass
class Credentials:
    access_token: str
    expires_at_seconds: int
    refresh_token: str

    def is_expired(self):
        return self.expires_at_seconds - _REFRESH_BUFFER < int(time.time())

    def parse_account_ids(self):
        account_ids = []
        org_id_to_org_member_info = _decode_jwt(self.access_token)[
            "org_id_to_org_member_info"
        ]
        for _, org_member_info in org_id_to_org_member_info.items():
            account_ids.append(org_member_info["org_metadata"]["account_id"])
        return account_ids


@dataclasses.dataclass()
class LaunchFlowConfig:
    credentials: Optional[Credentials]
    # NOTE: this is lazy loaded since it requires network operations
    env: LaunchFlowEnvVars

    @property
    def session(self) -> LaunchFlowSession:
        return LaunchFlowSession.load()

    @property
    def launchflow_yaml(self) -> LaunchFlowDotYaml:
        """This is a property so it can be lazily loaded."""
        try:
            return load_launchflow_dot_yaml()
        except FileNotFoundError:
            raise exceptions.LaunchFlowYamlNotFound()

    @property
    def project(self):
        # Environment variable takes precedence
        if self.env.project is not None:
            return self.env.project
        # Then launchflow.yaml
        try:
            return self.launchflow_yaml.project
        except exceptions.LaunchFlowYamlNotFound:
            # Default to None if launchflow.yaml is not found
            return None

    @property
    def environment(self):
        # Environment variable takes precedence
        if self.env.environment is not None:
            return self.env.environment
        # Then launchflow.yaml
        try:
            return self.launchflow_yaml.default_environment
        except exceptions.LaunchFlowYamlNotFound:
            # Default to None if launchflow.yaml is not found
            return None

    @property
    def backend(self):
        try:
            return self.launchflow_yaml.backend
        except exceptions.LaunchFlowYamlNotFound:
            # Default to None if launchflow.yaml is not found
            return None

    @property
    def ignore_roots(self):
        default_ignore_roots = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "dist",
            "build",
            ".pyenv",
        ]
        # Check if the user set the root directories to ignore in the launchflow.yaml
        try:
            if self.launchflow_yaml.ignore_roots is not None:
                return self.launchflow_yaml.ignore_roots
            return default_ignore_roots
        except exceptions.LaunchFlowYamlNotFound:
            return default_ignore_roots

    @classmethod
    def load(cls):
        credentials = None
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH) as f:
                credentials = Credentials(**toml.load(f))

        launchflow_env = load_launchflow_env()

        return cls(
            credentials=credentials,
            env=launchflow_env,
        )

    def _get_launchflow_backend(self) -> LaunchFlowBackend:
        try:
            backend = self.launchflow_yaml.backend
            backend_options = self.launchflow_yaml.backend_options
            if isinstance(backend, LaunchFlowBackend):
                return backend
        except exceptions.LaunchFlowYamlNotFound:
            backend_options = BackendOptions()
        # Default to creating a new LaunchFlowBackend if the launchflow.yaml is not
        # found or the backend is not a LaunchFlowBackend
        return LaunchFlowBackend.parse_backend("lf://default", backend_options)

    def get_launchflow_cloud_url(self) -> str:
        return self._get_launchflow_backend().lf_cloud_url

    def get_account_id(self) -> str:
        configured_account_id = self.get_configured_account_id()
        # When the account id is set to "default", we fetch the account id from the
        # credentials JWT token
        if configured_account_id == "default":
            if self.credentials is None:
                raise exceptions.NoLaunchFlowCredentials()
            account_ids = self.credentials.parse_account_ids()
            if len(account_ids) == 0:
                raise exceptions.NoLaunchFlowCredentials()
            elif len(account_ids) > 1:
                raise exceptions.CannotDefaultMultipleAccounts(account_ids)
            return account_ids[0]
        return configured_account_id

    def get_configured_account_id(self) -> str:
        return self._get_launchflow_backend().account_id

    def save(self):
        if self.credentials is not None:
            os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
            with open(CREDENTIALS_PATH, "w") as f:
                toml.dump(dataclasses.asdict(self.credentials), f)
        # Remove credentials file if it exists but credentials is None
        elif os.path.exists(CREDENTIALS_PATH):
            os.remove(CREDENTIALS_PATH)

    def set_api_key(self, api_key):
        self.env.api_key = api_key

    def get_access_token(self):
        if self.env.api_key:
            return self.env.api_key
        if self.credentials is None:
            raise exceptions.NoLaunchFlowCredentials()
        if self.credentials.is_expired():
            response = requests.post(
                f"{self.get_launchflow_cloud_url()}/auth/refresh",
                json={"refresh_token": self.credentials.refresh_token},
            )
            if response.status_code != 200:
                raise exceptions.LaunchFlowRequestFailure(response)
            self.update_credentials(response.json())
        return self.credentials.access_token

    def update_credentials(self, credentials_json: Dict[str, Any]):
        self.credentials = Credentials(**credentials_json)
        self.save()

    def clear_credentials(self):
        self.credentials = None
        self.save()
