import base64
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

import toml
import yaml

from launchflow.config import config


def encode_resource_outputs_cache(resource_outputs: Dict[str, Dict[str, str]]):
    """
    Encodes a dictionary into a Base64 string.

    Args:
        resource_outputs: A dict that maps resource name to a dict of outputs

    Returns:
        str: The Base64 encoded string of the dictionary.
    """

    def encode_yaml_content(yaml_content):
        return base64.b64encode(yaml.dump(yaml_content).encode("utf-8")).decode("utf-8")

    # Encode the YAML contents in the inner dictionaries
    encoded_dict = {
        key: encode_yaml_content(value) for key, value in resource_outputs.items()
    }

    # Serialize the dictionary to a JSON formatted string
    json_serialized = json.dumps(encoded_dict)

    # Encode the JSON string in Base64
    encoded_json = base64.b64encode(json_serialized.encode("utf-8")).decode("utf-8")

    return encoded_json


def decode_resource_outputs_cache(encoded_dict: str) -> Dict[str, Dict[str, str]]:
    """
    Decodes a Base64 string back into a dictionary.

    Args:
        encoded_dict (str): The Base64 encoded string to decode.

    Returns:
        dict: The decoded dictionary.
    """

    def decode_yaml_content(encoded_content):
        return yaml.safe_load(
            base64.b64decode(encoded_content.encode("utf-8")).decode("utf-8")
        )

    # Decode the Base64 string back to a JSON string
    decoded_json = base64.b64decode(encoded_dict.encode("utf-8")).decode("utf-8")

    # Deserialize the JSON string back to a dictionary
    deserialized_dict = json.loads(decoded_json)

    # Decode the YAML contents in the inner dictionaries
    decoded_dict = {
        key: decode_yaml_content(value) for key, value in deserialized_dict.items()
    }

    return decoded_dict


def build_cache_key(project: str, environment: str, product: str, resource: str) -> str:
    return f"{project}:{environment}:{product}:{resource}"


@dataclass
class LaunchFlowCache:
    permanent_cache_file_path: str

    # Permanent cache values below
    resource_connection_bucket_paths: Dict[str, str] = field(default_factory=dict)
    gcp_service_account_emails: Dict[str, str] = field(default_factory=dict)

    # In-memory cache values below
    resource_connection_info: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def get_resource_outputs_bucket_path(
        self, project: str, environment: str, product: str, resource: str
    ) -> Optional[str]:
        key = build_cache_key(project, environment, product, resource)
        return self.resource_connection_bucket_paths.get(key)

    def set_resource_connection_bucket_path(
        self,
        project: str,
        environment: str,
        product: str,
        resource: str,
        connection_bucket_path: str,
    ):
        key = build_cache_key(project, environment, product, resource)
        self.resource_connection_bucket_paths[key] = connection_bucket_path
        self.save_permanent_cache_to_disk()

    def delete_resource_connection_bucket_path(
        self, project: str, environment: str, product: str, resource: str
    ):
        key = build_cache_key(project, environment, product, resource)
        self.resource_connection_bucket_paths.pop(key, None)
        self.save_permanent_cache_to_disk()

    def get_resource_outputs(
        self,
        project: str,
        environment: str,
        product: str,
        resource_name: str,
    ) -> Optional[Dict[str, str]]:
        key = build_cache_key(project, environment, product, resource_name)
        return self.resource_connection_info.get(key)

    def set_resource_outputs(
        self,
        project: str,
        environment: str,
        product: str,
        resource_name: str,
        connection_info: Dict[str, str],
    ):
        key = build_cache_key(project, environment, product, resource_name)
        self.resource_connection_info[key] = connection_info

    def delete_resource_outputs(
        self, project: str, environment: str, product: str, resource: str
    ):
        key = build_cache_key(project, environment, product, resource)
        self.resource_connection_info.pop(key, None)
        self.save_permanent_cache_to_disk()

    def get_gcp_service_account_email(
        self, project: str, environment: str
    ) -> Optional[str]:
        key = f"{project}:{environment}"
        return self.gcp_service_account_emails.get(key)

    def set_gcp_service_account_email(self, project: str, environment: str, email: str):
        key = f"{project}:{environment}"
        self.gcp_service_account_emails[key] = email
        self.save_permanent_cache_to_disk()

    def delete_gcp_service_account_email(self, project: str, environment: str):
        key = f"{project}:{environment}"
        self.gcp_service_account_emails.pop(key, None)
        self.save_permanent_cache_to_disk()

    @classmethod
    def load_from_file(cls, permanent_cache_file_path: str):
        if not os.path.exists(permanent_cache_file_path):
            logging.debug(
                f"The file '{permanent_cache_file_path}' does not exist. Creating with default values."
            )
            return cls(
                permanent_cache_file_path=permanent_cache_file_path,
            )

        # Load the permanent cache
        with open(permanent_cache_file_path, "r") as file:
            logging.debug(f"Loading permanent cache from {permanent_cache_file_path}")
            data = toml.load(file)
            resource_connection_bucket_paths = data.get(
                "resource_connection_bucket_paths", {}
            )
            gcp_service_account_emails = data.get("gcp_service_account_emails", {})

        resource_connection_info = {}
        if config.env.run_cache is not None:
            logging.debug("Loading run cache from enviroment")
            # TODO: Add support for caching service outputs as well
            resource_connection_info = decode_resource_outputs_cache(
                config.env.run_cache
            )

        return cls(
            permanent_cache_file_path=permanent_cache_file_path,
            resource_connection_bucket_paths=resource_connection_bucket_paths,
            resource_connection_info=resource_connection_info,
            gcp_service_account_emails=gcp_service_account_emails,
        )

    def save_permanent_cache_to_disk(self):
        data = {
            "resource_connection_bucket_paths": self.resource_connection_bucket_paths,
            "gcp_service_account_emails": self.gcp_service_account_emails,
        }
        os.makedirs(os.path.dirname(self.permanent_cache_file_path), exist_ok=True)
        with open(self.permanent_cache_file_path, "w") as file:
            toml.dump(data, file)
        logging.debug(f"Saved to {self.permanent_cache_file_path}")

    def save_run_cache_to_disk(self):
        if self.run_cache_file_path is None:
            return
        data = {
            "resource_connection_info": self.resource_connection_info,
        }
        os.makedirs(os.path.dirname(self.run_cache_file_path), exist_ok=True)
        with open(self.run_cache_file_path, "w") as file:
            toml.dump(data, file)
        logging.debug(f"Saved to {self.run_cache_file_path}")


def build_cache_file_path():
    # We use /var/tmp over /tmp since it persists across system reboot
    permanent_tmp_dir = "/var/tmp" if os.name != "nt" else os.environ.get("TEMP")
    return os.path.join(permanent_tmp_dir, "lf", "cache.toml")


launchflow_cache = None


def load_launchflow_cache():
    global launchflow_cache
    if launchflow_cache is None:
        permanent_cache_file_path = build_cache_file_path()
        launchflow_cache = LaunchFlowCache.load_from_file(permanent_cache_file_path)
    return launchflow_cache
