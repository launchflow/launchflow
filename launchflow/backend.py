import enum
import logging
from dataclasses import dataclass
from typing import Literal, Optional, Union

from launchflow import exceptions


class BackendProtocol(enum.Enum):
    LOCAL = "file://"
    GCS = "gs://"
    LAUNCHFLOW_CLOUD = "lf://"


# TODO: explore the idea of having a separate BackendOptions class for each backend
@dataclass
class BackendOptions:
    lf_backend_url: Optional[str] = None

    def is_empty(self):
        return self.lf_backend_url is None

    def to_dict(self):
        return {
            "lf_backend_url": self.lf_backend_url,
        }

    def warn_if_non_local_fields_set(self):
        if self.lf_backend_url is not None:
            logging.warning(
                "The lf_backend_url option is ignored when using a local backend."
            )

    def warn_if_non_gcs_fields_set(self):
        if self.lf_backend_url is not None:
            logging.warning(
                "The lf_backend_url option is ignored when using a GCS backend."
            )

    def warn_if_non_lf_cloud_fields_set(self):
        # NOTE: All options are specific to the LaunchFlow Cloud backend at the moment
        pass


@dataclass
class Backend:
    @classmethod
    def parse_backend(
        cls, backend_str: str, backend_options: BackendOptions
    ) -> "Backend":
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError

    def protocol(self) -> BackendProtocol:
        raise NotImplementedError


@dataclass
class DockerBackend(Backend):
    pass


@dataclass
class LocalBackend(Backend):
    path: str

    @classmethod
    def parse_backend(
        cls, backend_str: str, backend_options: BackendOptions = BackendOptions()
    ) -> "LocalBackend":
        backend_options.warn_if_non_local_fields_set()
        _, path = backend_str.split("://", 1)
        return cls(path=path)

    def to_str(self) -> str:
        return f"{self.protocol().value}{self.path}"

    def protocol(self) -> BackendProtocol:
        return BackendProtocol.LOCAL


@dataclass
class LaunchFlowBackend(Backend):
    account_id: Union[Literal["default"], str] = "default"
    # TODO: Change these to the prod endpoints
    lf_cloud_url: str = "https://cloud.launchflow.com"

    @classmethod
    def parse_backend(
        cls, backend_str: str, backend_options: BackendOptions = BackendOptions()
    ) -> "LaunchFlowBackend":
        backend_options.warn_if_non_lf_cloud_fields_set()
        lf_cloud_url = backend_options.lf_backend_url or "https://cloud.launchflow.com"
        _, account_id = backend_str.split("://", 1)
        # TODO: add validation to make sure the account id format is correct
        if not account_id:
            raise exceptions.InvalidBackend(
                f"Invalid backend: {backend_str}. It must be in the format `lf://<account_id>` or `lf://default`."
            )
        return cls(
            account_id=account_id,
            lf_cloud_url=lf_cloud_url,
        )

    def to_str(self) -> str:
        return f"{self.protocol().value}{self.account_id}"

    def protocol(self) -> BackendProtocol:
        return BackendProtocol.LAUNCHFLOW_CLOUD


@dataclass
class GCSBackend(Backend):
    bucket: str
    prefix: str = ""

    @classmethod
    def parse_backend(
        cls, backend_str: str, backend_options: BackendOptions = BackendOptions()
    ) -> "GCSBackend":
        backend_options.warn_if_non_gcs_fields_set()
        _, full_bucket_path = backend_str.split("://", 1)
        split_bucket_path = full_bucket_path.split("/")
        bucket = split_bucket_path[0]
        prefix = "/".join(split_bucket_path[1:]) or ""
        return cls(bucket=bucket, prefix=prefix)

    def to_str(self) -> str:
        return f"{self.protocol().value}{self.bucket}"

    def protocol(self) -> BackendProtocol:
        return BackendProtocol.GCS


def parse_backend_protocol_str(
    backend_str: str, backend_options: BackendOptions
) -> Backend:
    if backend_str.startswith(BackendProtocol.LOCAL.value):
        return LocalBackend.parse_backend(backend_str, backend_options)
    elif backend_str.startswith(BackendProtocol.GCS.value):
        return GCSBackend.parse_backend(backend_str, backend_options)
    elif backend_str.startswith(BackendProtocol.LAUNCHFLOW_CLOUD.value):
        return LaunchFlowBackend.parse_backend(backend_str, backend_options)
    else:
        raise ValueError(f"Invalid backend: {backend_str}")
