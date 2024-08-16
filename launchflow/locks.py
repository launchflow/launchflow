import dataclasses
import enum
import json
import os
import uuid
from typing import Any, Dict, Optional

import httpx

from launchflow import exceptions
from launchflow.config import config
from launchflow.gcp_clients import get_storage_client


class OperationType(enum.Enum):
    CREATE_ENVIRONMENT = "create_environment"
    DELETE_ENVIRONMENT = "delete_environment"
    MIGRATE_ENVIRONMENT = "migrate_environment"
    # Resources
    CREATE_RESOURCE = "create_resource"
    UPDATE_RESOURCE = "update_resource"
    REPLACE_RESOURCE = "replace_resource"
    DESTROY_RESOURCE = "destroy_resource"
    MIGRATE_RESOURCE = "migrate_resource"
    IMPORT_RESOURCE = "import_resource"
    # Services
    CREATE_SERVICE = "create_service"
    UPDATE_SERVICE = "update_service"
    DEPLOY_SERVICE = "deploy_service"
    DESTROY_SERVICE = "destroy_service"
    PROMOTE_SERVICE = "promote_service"
    MIGRATE_SERVICE = "migrate_service"
    # This is used when resources / services are being creating in an environment
    LOCK_ENVIRONMENT = "lock_environment"


class ReleaseReason(enum.Enum):
    ABANDONED = "abandoned"
    COMPLETED = "completed"


@dataclasses.dataclass
class LockOperation:
    operation_type: OperationType
    metadata: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class LockInfo:
    lock_id: str
    lock_operation: LockOperation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lock_id": self.lock_id,
            "lock_operation": {
                "operation_type": self.lock_operation.operation_type.value,
                "metadata": self.lock_operation.metadata,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LockInfo":
        return cls(
            lock_id=data["lock_id"],
            lock_operation=LockOperation(
                operation_type=OperationType(data["lock_operation"]["operation_type"]),
                metadata=data["lock_operation"]["metadata"],
            ),
        )


class Lock:
    def __init__(self, operation: LockOperation) -> None:
        self._lock_info: Optional[LockInfo] = None
        self.operation = operation

    @property
    def lock_info(self) -> LockInfo:
        if self._lock_info is None:
            raise exceptions.LockNotAcquired()
        return self._lock_info

    async def acquire(self) -> LockInfo:
        raise NotImplementedError

    async def release(self, reason: ReleaseReason = ReleaseReason.COMPLETED) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> LockInfo:
        # First check if the lock as already been acquired
        if self._lock_info is None:
            self._lock_info = await self.acquire()
        return self._lock_info

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # TODO: consider adding a log message to let the user know we're releasing the lock when an exception is raised
        # (maybe only do this on ctrl-c)
        try:
            await self.release()
            self._lock_info = None
        except FileNotFoundError:
            # Swallow the error if the lock file is missing
            # this means the lock has already been released.
            # This can happen if a directory is deleted for example
            # when an environment is deleted.
            pass


class DockerLock(Lock):
    """Trivial lock that does nothing, since local docker doesn't need locks."""

    def __init__(self, operation: LockOperation) -> None:
        super().__init__(operation=operation)

    async def acquire(self) -> LockInfo:
        self._lock_info = LockInfo(lock_id="docker", lock_operation=self.operation)
        return self._lock_info

    async def release(self, reason: ReleaseReason = ReleaseReason.COMPLETED) -> None:
        self._lock_info = None


class LocalLock(Lock):
    def __init__(self, file_path: str, operation: LockOperation) -> None:
        super().__init__(operation=operation)
        self.file_path = file_path
        self.operation = operation

    async def acquire(self) -> LockInfo:
        try:
            self._lock_info = LockInfo(str(uuid.uuid4()), self.operation)
            if not os.path.exists(self.file_path):
                os.makedirs(self.file_path)
            with open(os.path.join(self.file_path, "flow.lock"), "x") as f:
                json.dump(self._lock_info.to_dict(), f)
            return self._lock_info
        except FileExistsError:
            raise exceptions.EntityLocked(self.file_path)

    async def release(self, reason: ReleaseReason = ReleaseReason.COMPLETED) -> None:
        if self._lock_info is not None:
            with open(os.path.join(self.file_path, "flow.lock"), "r") as f:
                lock = LockInfo.from_dict(json.load(f))
                if lock.lock_id == self._lock_info.lock_id:
                    os.remove(os.path.join(self.file_path, "flow.lock"))
                else:
                    raise exceptions.LockMismatch(self.file_path)
            self._lock_info = None

    @staticmethod
    async def force_unlock(file_path: str) -> None:
        lock_file = os.path.join(file_path, "flow.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
        else:
            raise exceptions.LockNotFound(file_path)


class GCSLock(Lock):
    def __init__(
        self,
        bucket: str,
        prefix: str,
        project_name: str,
        entity_file_path: str,
        operation: LockOperation,
    ) -> None:
        super().__init__(operation=operation)
        self.bucket = bucket
        self.prefix = prefix
        # TODO: maybe operation should be move to the aquire method instead
        self.operation = operation
        self.entity_file_path = os.path.join(project_name, entity_file_path)
        self.lock_path = os.path.join(self.prefix, self.entity_file_path, "flow.lock")

    async def acquire(self) -> LockInfo:
        """Acquire a lock in GCS.

        The basic algorithm is:
        1. Create a blob with `if_generation_match=0`
        2. If this fails we know the lock already exists
        3. Return the lock info to the caller to allow them to unlock
        """
        try:
            from google.api_core.exceptions import PreconditionFailed
        except ImportError:
            raise exceptions.MissingGCPDependency()
        try:
            lock_info = LockInfo(str(uuid.uuid4()), self.operation)
            client = get_storage_client()
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(self.lock_path)
            blob.upload_from_string(
                json.dumps(lock_info.to_dict()),
                if_generation_match=0,
            )
            self._lock_info = lock_info
            return self._lock_info
        except PreconditionFailed:
            raise exceptions.EntityLocked(self.entity_file_path)

    async def release(self, reason: ReleaseReason = ReleaseReason.COMPLETED) -> None:
        """Release the lock from GCS.

        The basic algorithm is:
        1. Download the lock file
        2. Verify the client unlocking is the same as the client locking
        3. Delete the lock file to release the lock
        """
        if self._lock_info is not None:
            read_lock_info = await self.read_lock()
            if read_lock_info is None:
                # Swallow the error if the lock file is missing
                self._lock_info = None
                return
            if read_lock_info.lock_id == self._lock_info.lock_id:
                client = get_storage_client()
                bucket = client.bucket(self.bucket)
                blob = bucket.blob(self.lock_path)
                blob.delete()
            self._lock_info = None

    async def read_lock(self) -> Optional[LockInfo]:
        try:
            from google.api_core.exceptions import NotFound
        except ImportError:
            raise exceptions.MissingGCPDependency()
        client = get_storage_client()
        bucket = client.bucket(self.bucket)
        blob = bucket.blob(self.lock_path)
        try:
            json_data = json.loads(blob.download_as_bytes().decode("utf-8"))
            remote_lock_info = LockInfo.from_dict(json_data)
            return remote_lock_info
        except NotFound:
            return None

    @staticmethod
    async def force_unlock(
        bucket: str, prefix: str, project_name: str, entity_file_path: str
    ) -> None:
        try:
            from google.api_core.exceptions import NotFound
        except ImportError:
            raise exceptions.MissingGCPDependency()
        client = get_storage_client()
        gcs_bucket = client.bucket(bucket)
        blob = gcs_bucket.blob(
            os.path.join(prefix, project_name, entity_file_path, "flow.lock")
        )
        try:
            blob.delete()
        except NotFound:
            raise exceptions.LockNotFound(entity_file_path)


class LaunchFlowLock(Lock):
    def __init__(
        self,
        project: str,
        entity_path: str,
        operation: LockOperation,
        launch_url: str,
        launchflow_account_id: str,
    ) -> None:
        super().__init__(operation=operation)
        self.project = project
        self.entity_path = entity_path
        launch_service_url = (
            f"{launch_url}/v1/projects/{self.project}/{self.entity_path}"
        )
        self.lock_url = f"{launch_service_url}/lock?account_id={launchflow_account_id}"
        self.unlock_url = f"{launch_service_url}/unlock"
        self.operation = operation
        self.launchflow_account_id = launchflow_account_id

    async def acquire(self) -> LockInfo:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.lock_url,
                json={
                    "operation": self.operation.operation_type.value,
                    "metadata": self.operation.metadata,
                },
                headers={"Authorization": f"Bearer {config.get_access_token()}"},
            )
            if response.status_code == 423:
                raise exceptions.EntityLocked(self.entity_path)
            if response.status_code != 200:
                raise exceptions.LaunchFlowRequestFailure(response)
            self._lock_info = LockInfo.from_dict(response.json())
            return self._lock_info

    async def release(self, reason: ReleaseReason = ReleaseReason.COMPLETED) -> None:
        if self._lock_info is not None:
            # TODO: probably want to add some retries to make sure this always works
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.unlock_url}?lock_id={self._lock_info.lock_id}&account_id={self.launchflow_account_id}",
                    json={"reason": reason.value},
                    headers={"Authorization": f"Bearer {config.get_access_token()}"},
                )
                # The lock may have been deleted if the environment was deleted
                if response.status_code != 200 and response.status_code != 404:
                    raise exceptions.LaunchFlowRequestFailure(response)
            self._lock_info = None

    @staticmethod
    async def force_unlock(
        project: str,
        entity_path: str,
        launch_url: str,
        launchflow_account_id: str,
    ):
        access_token = config.get_access_token()
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{launch_url}/v1/projects/{project}/{entity_path}/force_unlock?account_id={launchflow_account_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 404:
                raise exceptions.LockNotFound(entity_path)
            if response.status_code == 409:
                raise exceptions.EntityNotLocked(entity_path)
            if response.status_code != 200:
                raise exceptions.LaunchFlowRequestFailure(response)
