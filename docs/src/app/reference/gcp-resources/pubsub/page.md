# GCP Cloud Pub/Sub Resources

Resources for [Google Cloud Pub/Sub](https://cloud.google.com/pubsub). Available resources include:
- [`PubsubTopic`](https://docs.launchflow.com/reference/gcp-resources/pubsub#pubsub-topic): A GCP Cloud Pub/Sub Topic.
- [`PubsubSubscription`](https://docs.launchflow.com/reference/gcp-resources/pubsub#pubsub-subscription): A GCP Cloud Pub/Sub Subscription.

## Example Usage

### Create a Pub/Sub Topic
```python
import launchflow as lf

# Automatically creates / connects to a PubSub Topic in your GCP project
topic = lf.gcp.PubsubTopic("my-pubsub-topic")

topic.publish(b"Hello, world!")
```

### Create a Pub/Sub Subscription
```python
import launchflow as lf

topic = lf.gcp.PubsubTopic("my-pubsub-topic")
# Automatically creates / connects to a PubSub Subscription in your GCP project
subscription = lf.gcp.PubsubSubscription("my-pubsub-sub", topic=topic)
```

## PubsubSubscription

A GCP Cloud Pub/Sub Subscription.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/pubsub/docs/overview).

### Example Usage
```python
import launchflow as lf

topic = lf.gcp.PubsubTopic("my-pubsub-topic")
# Automatically creates / connects to a PubSub Subscription in your GCP project
subscription = lf.gcp.PubsubSubscription("my-pubsub-sub", topic=topic)
```

### initialization

Create a new PubsubSubscription resource.

**Args:**
- `name (str)`: The name of the PubsubSubscription resource.
- `topic (Union[PubsubTopic, str])`: The topic to subscribe to.
- `push_config (Optional[PushConfig])`: The push configuration for the subscription.
- `ack_deadline_seconds (int)`: The acknowledgment deadline for the subscription.
- `message_retention_duration (datetime.timedelta)`: The message retention duration for the subscription.
- `retain_acked_messages (bool)`: Whether to retain acknowledged messages.
- `filter (Optional[str])`: The filter for the subscription.

**Raises:***:
- `ValueError`: If the topic is not a PubsubTopic or a str.

### inputs

```python
PubsubSubscription.inputs(environment_state: EnvironmentState) -> PubsubSubscriptionInputs
```

Get the inputs for the PubsubSubscription resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `PubsubSubscriptionInputs`: The inputs for the PubsubSubscription resource.

## PubsubTopic

A GCP Cloud Pub/Sub Topic.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/pubsub/docs/overview).

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to a PubSub Topic in your GCP project
topic = lf.gcp.PubsubTopic("my-pubsub-topic")

topic.publish(b"Hello, world!")
```

### initialization

Create a new PubsubTopic resource.

**Args:**
- `name (str)`: The name of the PubsubTopic resource.
- `message_retention_duration (Optional[datetime.timedelta])`: The message retention duration for the topic.

**Raises:***:
- `ValueError`: If the message retention duration is not within the allowed range.

### inputs

```python
PubsubTopic.inputs(environment_state: EnvironmentState) -> PubsubTopicInputs
```

Get the inputs for the PubsubTopic resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `PubsubTopicInputs`: The inputs for the PubsubTopic resource.

### publish

```python
PubsubTopic.publish(data: bytes, ordering_key: str = "")
```

Publish a message to the topic.

**Args:**
- `data (bytes)`: The bytes to publish in the message.
- `ordering_key (str)`: An optional ordering key for the message.

**Returns:**
- The result of the publish operation.

**Raises:***:
- `ImportError`: If the google-cloud-pubsub library is not installed.

**Example usage:**

```python
import launchflow as lf

topic = lf.gcp.PubsubTopic("my-pubsub-topic")

topic.publish(b"Hello, world!")
```

### publish\_async

```python
async PubsubTopic.publish_async(data: bytes, ordering_key: str = "")
```

Asynchronously publish a message to the topic.

**Args:**
- `data (bytes)`: The bytes to publish in the message.
- `ordering_key (str)`: An optional ordering key for the message.

**Returns:**
- The result of the publish operation.

**Raises:***:
- `ImportError`: If the google-cloud-pubsub library is not installed.

**Example usage:**

```python
import launchflow as lf

topic = lf.gcp.PubsubTopic("my-pubsub-topic")

await topic.publish_async(b"Hello, world!")
```
