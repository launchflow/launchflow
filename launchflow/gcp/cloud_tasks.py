import dataclasses
import datetime
import json as _json
from typing import Dict, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs

try:
    from google.cloud import tasks
except ImportError:
    tasks = None  # type: ignore


@dataclasses.dataclass
class CloudTasksQueueOutputs(Outputs):
    queue_id: str


@dataclasses.dataclass
class CloudTasksQueueInputs(ResourceInputs):
    location: Optional[str]


# TODO: add methods that automatically enqueue a task with
# the environment credentials
class CloudTasksQueue(GCPResource[CloudTasksQueueOutputs]):
    # TODO: clean up example
    """A GCP Cloud Tasks Queue.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/tasks/docs/).

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to a Cloud Tasks Queue in your GCP project
    queue = lf.gcp.CloudTasksQueue("my-queue")

    queue.enqueue("https://example.com/endpoint", json={"key": "value"})
    ```
    """

    product = ResourceProduct.GCP_CLOUD_TASKS_QUEUE.value

    def __init__(self, name: str, location: Optional[str] = None) -> None:
        """Create a new CloudTasksQueue.

        **Args:**
        - `name (str)`: The name of the Cloud Tasks Queue.
        - `location (Optional[str])`: The location of the queue. If None, the environments default region is used. Defaults to None.
        """
        super().__init__(
            name=name,
            replacement_arguments={"location"},
        )
        self.location = location

    def inputs(self, environment_state: EnvironmentState) -> CloudTasksQueueInputs:
        return CloudTasksQueueInputs(
            resource_id=self.resource_id, location=self.location
        )

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        location = self.location or environment_state.gcp_config.default_region  # type: ignore
        return {"google_cloud_tasks_queue.queue": f"{location}/{self.name}"}

    def enqueue(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        json: Optional[Dict] = None,
        oauth_token: Optional[str] = None,
        oidc_token: Optional[str] = None,
        schedule_time: Optional[datetime.datetime] = None,
    ) -> "tasks.Task":
        """Enqueue a task in the Cloud Tasks queue.

        **Args:**
        - `url (str)`: The url the task will call.
        - `method (str)`: The HTTP method to use. Defaults to "POST".
        - `headers (Optional[Dict[str, str]])`: A dictionary of headers to include in the request.
        - `body (Optional[bytes])`: The body of the request. Only one of `body` or `json` can be provided.
        - `json (Optional[Dict])`: A dictionary to be serialized as JSON and sent as the body of the request. Only one of `body` or `json` can be provided.
        - `oauth_token (Optional[str])`: An OAuth token to include in the request.
        - `oidc_token (Optional[str])`: An OIDC token to include in the request.
        - `schedule_time (Optional[datetime.datetime])`: The time to schedule the task for.

        **Returns:**
        - [`tasks.Task`](https://cloud.google.com/python/docs/reference/cloudtasks/latest/google.cloud.tasks_v2.types.Task): The created GCP cloud task.

        **Raises:**
        - `ImportError`: If the google-cloud-tasks library is not installed.
        - `ValueError`: If both `body` and `json` are provided.

        **Example usage:**
        ```python
        import launchflow as lf

        queue = lf.gcp.CloudTasksQueue("my-queue")

        queue.enqueue("https://example.com/endpoint", json={"key": "value"})
        ```
        """
        if tasks is None:
            raise ImportError(
                "google-cloud-tasks not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        if body is not None and json is not None:
            raise ValueError("Cannot provide both body and json")
        if body is None and json is not None:
            body = _json.dumps(json).encode("utf-8")
        info = self.outputs()
        client = tasks.CloudTasksClient()
        return client.create_task(
            parent=info.queue_id,
            task=tasks.Task(
                http_request=tasks.HttpRequest(
                    url=url,
                    http_method=method,
                    headers=headers,
                    body=body,
                    oauth_token=oauth_token,
                    oidc_token=oidc_token,
                ),
                schedule_time=schedule_time,
            ),
        )

    async def enqueue_async(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        json: Optional[Dict] = None,
        oauth_token: Optional[str] = None,
        oidc_token: Optional[str] = None,
        schedule_time: Optional[datetime.datetime] = None,
    ) -> "tasks.Task":
        """Asynchronously enqueue a task in the Cloud Tasks queue.

        **Args:**
        - `url (str)`: The url the task will call.
        - `method (str)`: The HTTP method to use. Defaults to "POST".
        - `headers (Optional[Dict[str, str]])`: A dictionary of headers to include in the request.
        - `body (Optional[bytes])`: The body of the request. Only one of `body` or `json` can be provided.
        - `json (Optional[Dict])`: A dictionary to be serialized as JSON and sent as the body of the request. Only one of `body` or `json` can be provided.
        - `oauth_token (Optional[str])`: An OAuth token to include in the request.
        - `oidc_token (Optional[str])`: An OIDC token to include in the request.
        - `schedule_time (Optional[datetime.datetime])`: The time to schedule the task for.

        **Returns:**
        - [`tasks.Task`](https://cloud.google.com/python/docs/reference/cloudtasks/latest/google.cloud.tasks_v2.types.Task): The created GCP cloud task.

        **Raises:**
        - `ImportError`: If the google-cloud-tasks library is not installed.
        - `ValueError`: If both `body` and `json` are provided.

        **Example usage:**
        ```python
        import launchflow as lf

        queue = lf.gcp.CloudTasksQueue("my-queue")

        await queue.enqueue_async("https://example.com/endpoint", json={"key": "value"})
        ```
        """
        if tasks is None:
            raise ImportError(
                "google-cloud-tasks not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        if body is not None and json is not None:
            raise ValueError("Cannot provide both body and json")
        if body is None and json is not None:
            body = _json.dumps(json).encode("utf-8")
        info = await self.outputs_async()
        client = tasks.CloudTasksAsyncClient()
        return await client.create_task(
            parent=info.queue_id,
            task=tasks.Task(
                http_request=tasks.HttpRequest(
                    url=url,
                    http_method=method,
                    headers=headers,
                    body=body,
                    oauth_token=oauth_token,
                    oidc_token=oidc_token,
                ),
                schedule_time=schedule_time,
            ),
        )
