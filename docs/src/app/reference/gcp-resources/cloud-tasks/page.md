## CloudTasksQueue

A GCP Cloud Tasks Queue.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/tasks/docs/).

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to a Cloud Tasks Queue in your GCP project
queue = lf.gcp.CloudTasksQueue("my-queue")

queue.enqueue("https://example.com/endpoint", json={"key": "value"})
```

### initialization

Create a new CloudTasksQueue.

**Args:**
- `name (str)`: The name of the Cloud Tasks Queue.
- `location (Optional[str])`: The location of the queue. If None, the environments default region is used. Defaults to None.

### inputs

```python
CloudTasksQueue.inputs(environment_state: EnvironmentState) -> CloudTasksQueueInputs
```

Get the inputs for the CloudTasksQueue resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get the inputs for.

**Returns:**
- `CloudTasksQueueInputs`: The inputs for the CloudTasksQueue resource.

### enqueue

```python
CloudTasksQueue.enqueue(url: str, method: str = "POST", headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None, json: Optional[Dict] = None, oauth_token: Optional[str] = None, oidc_token: Optional[str] = None, schedule_time: Optional[datetime.datetime] = None) -> "tasks.Task"
```

Enqueue a task in the Cloud Tasks queue.

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

### enqueue\_async

```python
async CloudTasksQueue.enqueue_async(url: str, method: str = "POST", headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None, json: Optional[Dict] = None, oauth_token: Optional[str] = None, oidc_token: Optional[str] = None, schedule_time: Optional[datetime.datetime] = None) -> "tasks.Task"
```

Asynchronously enqueue a task in the Cloud Tasks queue.

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
