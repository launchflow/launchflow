"""
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

"""

try:
    from google.cloud.pubsub import PublisherClient  # type: ignore
    from google.pubsub_v1.services.publisher import PublisherAsyncClient
    from google.pubsub_v1.types import PubsubMessage
except ImportError:
    PublisherClient = None  # type: ignore
    PublisherAsyncClient = None  # type: ignore
    PubsubMessage = None  # type: ignore


import dataclasses
import datetime
from typing import Dict, Optional, Union

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class PubsubTopicOutputs(Outputs):
    topic_id: str


@dataclasses.dataclass
class PubsubTopicInputs(ResourceInputs):
    message_retention_duration: Optional[str]


class PubsubTopic(GCPResource[PubsubTopicOutputs]):
    """A GCP Cloud Pub/Sub Topic.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/pubsub/docs/overview).

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to a PubSub Topic in your GCP project
    topic = lf.gcp.PubsubTopic("my-pubsub-topic")

    topic.publish(b"Hello, world!")
    ```
    """

    product = ResourceProduct.GCP_PUBSUB_TOPIC.value

    def __init__(
        self, name: str, message_retention_duration: Optional[datetime.timedelta] = None
    ) -> None:
        """Create a new PubsubTopic resource.

        **Args:**
        - `name (str)`: The name of the PubsubTopic resource.
        - `message_retention_duration (Optional[datetime.timedelta])`: The message retention duration for the topic.

        **Raises:***:
        - `ValueError`: If the message retention duration is not within the allowed range.
        """
        super().__init__(name=name)
        if message_retention_duration is not None:
            if message_retention_duration > datetime.timedelta(days=31):
                raise ValueError(
                    "Message retention duration must be less than or equal to 31 days."
                )
            if message_retention_duration < datetime.timedelta(minutes=10):
                raise ValueError(
                    "Message retention duration must be greater than or equal to 10 minutes."
                )
        self.message_retention_duration = message_retention_duration

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        return {"google_pubsub_topic.topic": self.name}

    def inputs(self, environment_state: EnvironmentState) -> PubsubTopicInputs:
        if self.message_retention_duration is not None:
            duration_str = f"{int(self.message_retention_duration.total_seconds())}s"
        else:
            duration_str = None
        return PubsubTopicInputs(
            resource_id=self.resource_id,
            message_retention_duration=duration_str,
        )

    def publish(self, data: bytes, ordering_key: str = ""):
        """Publish a message to the topic.

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
        """
        if PublisherClient is None:
            raise ImportError(
                "google-cloud-pubsub not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        connection = self.outputs()
        client = PublisherClient()
        return client.publish(connection.topic_id, data, ordering_key=ordering_key)

    async def publish_async(self, data: bytes, ordering_key: str = ""):
        """Asynchronously publish a message to the topic.

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
        """
        if PublisherAsyncClient is None:
            raise ImportError(
                "google-cloud-pubsub not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        connection = await self.outputs_async()
        client = PublisherAsyncClient()
        return await client.publish(
            messages=[PubsubMessage(data=data, ordering_key=ordering_key)],
            topic=connection.topic_id,
        )


@dataclasses.dataclass
class OidcToken(Inputs):
    service_account_email: str
    audience: Optional[str] = None


@dataclasses.dataclass
class PushConfig(Inputs):
    push_endpoint: str
    oidc_token: Optional[OidcToken] = None
    attributes: Optional[Dict[str, str]] = None


@dataclasses.dataclass
class PubsubSubscriptionInputs(ResourceInputs):
    topic: str
    push_config: Optional[PushConfig]
    ack_deadline_seconds: int
    message_retention_duration: str
    retain_acked_messages: bool
    filter: Optional[str]


@dataclasses.dataclass
class PubsubSubscriptionOutputs(Outputs):
    subscription_id: str


class PubsubSubscription(GCPResource[PubsubSubscriptionOutputs]):
    """A GCP Cloud Pub/Sub Subscription.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/pubsub/docs/overview).

    ### Example Usage
    ```python
    import launchflow as lf

    topic = lf.gcp.PubsubTopic("my-pubsub-topic")
    # Automatically creates / connects to a PubSub Subscription in your GCP project
    subscription = lf.gcp.PubsubSubscription("my-pubsub-sub", topic=topic)
    ```
    """

    product = ResourceProduct.GCP_PUBSUB_SUBSCRIPTION.value

    # TODO: Add optional arguments for subscription settings
    def __init__(
        self,
        name: str,
        topic: Union[PubsubTopic, str],
        push_config: Optional[PushConfig] = None,
        ack_deadline_seconds: int = 10,
        message_retention_duration: datetime.timedelta = datetime.timedelta(days=7),
        retain_acked_messages: bool = False,
        filter: Optional[str] = None,
    ) -> None:
        """Create a new PubsubSubscription resource.

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
        """
        if not isinstance(topic, (PubsubTopic, str)):
            raise ValueError("topic must be a PubsubTopic or a str")

        self.topic = topic
        self.push_config = push_config
        self.ack_deadline_seconds = ack_deadline_seconds
        self.message_retention_duration = message_retention_duration
        self.retain_acked_messages = retain_acked_messages
        self.filter = filter
        super().__init__(name=name)

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        return {"google_pubsub_subscription.subscription": self.name}

    def inputs(self, environment_state: EnvironmentState) -> PubsubSubscriptionInputs:
        if isinstance(self.topic, PubsubTopic):
            topic_id = Depends(self.topic).topic_id  # type: ignore
        elif isinstance(self.topic, str):
            topic_id = self.topic
        else:
            raise ValueError("topic must be a PubsubTopic or a str")

        message_retention_duration = None
        if self.message_retention_duration is not None:
            message_retention_duration = (
                f"{int(self.message_retention_duration.total_seconds())}s"
            )
        return PubsubSubscriptionInputs(
            resource_id=self.resource_id,
            topic=topic_id,
            push_config=self.push_config,
            ack_deadline_seconds=self.ack_deadline_seconds,
            message_retention_duration=message_retention_duration,
            retain_acked_messages=self.retain_acked_messages,
            filter=self.filter,
        )
