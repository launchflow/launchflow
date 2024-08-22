import dataclasses
from datetime import timedelta
from typing import Any, Dict, Literal, Optional

from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore


from launchflow.aws.resource import AWSResource


@dataclasses.dataclass
class SQSQueueOutputs(Outputs):
    url: str


@dataclasses.dataclass
class SQSQueueInputs(ResourceInputs):
    delivery_delay_seconds: int
    max_message_size_bytes: int
    message_retention_period_seconds: int
    receive_wait_time_seconds: int
    visibility_timeout_seconds: int
    fifo_queue: bool
    content_based_deduplication: bool = False
    deduplication_scope: Optional[Literal["queue", "message_group"]] = None
    fifo_throughput_limit: Optional[Literal["perQueue", "perMessageGroupId"]] = (
        "perQueue"
    )


class SQSQueue(AWSResource[SQSQueueOutputs]):
    """A queue in AWS's SQS service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/sqs/).

    ### Example Usage

    #### Basic Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to a SQS Queue in your AWS account
    queue = lf.aws.SQSQueue("my-queue")

    # Quick utilities for sending and receiving messages
    queue.send_message("Hello, world!")
    ```

    #### FIFO Queue

    FIFO queues require a `.fifo` suffix and offer additional configuration.

    ```python
    import launchflow as lf

    # Automatically creates / connects to a FIFO SQS Queue in your AWS account
    # Note: FIFO queues require a `.fifo` suffix
    queue = lf.aws.SQSQueue("my-queue.fifo", fifo_queue=True)
    ```
    """

    product = ResourceProduct.AWS_SQS_QUEUE.value

    def __init__(
        self,
        name: str,
        *,
        delivery_delay: timedelta = timedelta(seconds=0),
        max_message_size_bytes: int = 262144,
        message_retention_period: timedelta = timedelta(seconds=345600),
        receive_wait_time: timedelta = timedelta(seconds=0),
        visibility_timeout: timedelta = timedelta(seconds=30),
        fifo_queue: bool = False,
        content_based_deduplication: bool = False,
        deduplication_scope: Optional[Literal["queue", "message_group"]] = None,
        fifo_throughput_limit: Optional[
            Literal["perQueue", "perMessageGroupId"]
        ] = None,
    ) -> None:
        """Create a new SQS queue resource.

        **Args:**
        - `name` (str): The name of the queue. This must be globally unique.
        - `delivery_delay (timedelta)`: The delay before all messages in the queue will be delivered. Defaults to 0 seconds.
        - `max_message_size_bytes (int)`: The maximum size of a message in the queue. Messages over this size will be rejected by AWS SQS. Defaults to 262144 (256 KiB)
        - `message_retention_period (timedelta)`: The length of time that a message will be retained in the queue. Defaults to 345600 seconds (4 days).
        - `receive_wait_time (timedelta)`: The length of time that a poll request will wait for a message to arrive in the queue. Defaults to 0 seconds.
        - `visibility_timeout (timedelta)`: After a message is received the period of time during which Amazon SQS prevents all consumers from receiving and processing the message. Defaults to 30 seconds.
        - `fifo_queue (bool)`: If true, the queue will be a FIFO queue. Defaults to False.
        - `content_based_deduplication (bool)`: If true, the queue will use content-based deduplication for fifo queues. Defaults to False.
        - `deduplication_scope (str)`: Whether deduplication should take place at the queue level or the group level. Can only be specified when `fifo_queue` is True. Defaults to "queue".
        - `fifo_throughput_limit (str)`: Whether the throughput limit should be per queue or per message group. Can only be specified when `fifo_queue` is True. Defaults to "perQueue".
        """
        super().__init__(name=name)
        self.delivery_delay = delivery_delay
        self.max_message_size_bytes = max_message_size_bytes
        self.message_retention_period = message_retention_period
        self.receive_wait_time = receive_wait_time
        self.visibility_timeout = visibility_timeout
        self.fifo_queue = fifo_queue
        self.content_based_deduplication = content_based_deduplication
        self.deduplication_scope = deduplication_scope
        self.fifo_throughput_limit = fifo_throughput_limit
        if not fifo_queue and content_based_deduplication:
            raise ValueError(
                "content_based_deduplication can only be set when fifo_queue is True"
            )
        if not fifo_queue and deduplication_scope:
            raise ValueError(
                "deduplication_scope can only be set when fifo_queue is True"
            )
        if fifo_queue and not name.endswith(".fifo"):
            raise ValueError("FIFO queues must have a name ending in .fifo")
        if delivery_delay.total_seconds() < 0 or delivery_delay.total_seconds() > 900:
            raise ValueError("delivery_delay must be between 0 and 900 seconds")
        if max_message_size_bytes < 1024 or max_message_size_bytes > 262144:
            raise ValueError(
                "max_message_size_bytes must be between 1024 and 262144 bytes"
            )
        if (
            message_retention_period.total_seconds() < 60
            or message_retention_period.total_seconds() > 1209600
        ):
            raise ValueError(
                "message_retention_period must be between 1 minutes and 14 days"
            )
        if (
            receive_wait_time.total_seconds() < 0
            or receive_wait_time.total_seconds() > 20
        ):
            raise ValueError("receive_wait_time must be between 0 and 20 seconds")

    def inputs(self, environment_state: EnvironmentState) -> SQSQueueInputs:
        return SQSQueueInputs(
            resource_id=self.resource_id,
            delivery_delay_seconds=int(self.delivery_delay.total_seconds()),
            max_message_size_bytes=self.max_message_size_bytes,
            message_retention_period_seconds=int(
                self.message_retention_period.total_seconds()
            ),
            receive_wait_time_seconds=int(self.receive_wait_time.total_seconds()),
            visibility_timeout_seconds=int(self.visibility_timeout.total_seconds()),
            fifo_queue=self.fifo_queue,
            content_based_deduplication=self.content_based_deduplication,
            deduplication_scope=self.deduplication_scope,
            fifo_throughput_limit=self.fifo_throughput_limit,
        )

    def send_message(
        self,
        message_body: str,
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Any]] = None,
        message_system_attributes: Optional[Dict[str, Any]] = None,
        message_deduplication_id: Optional[str] = None,
        message_group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the queue using the boto3 client library.

        For additional details on parameters and return type see the [client library documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs/client/send_message.html).

        **Args:**
        - `message_body (str)`: The message to send to the queue.
        - `delay_seconds (int)`: The number of seconds to delay the message. Defaults to 0.
        - `message_attributes (Dict[str, Any])`: Additional attributes for the message. Defaults to None.
        - `message_system_attributes (Dict[str, Any])`: Additional system attributes for the message. Defaults to None.
        - `message_deduplication_id (str)`: The token used for deduplication of sent messages. Defaults to None.
        - `message_group_id (str)`: The tag that specifies that a message belongs to a specific message group. Defaults to None.

        **Returns:**
        - `Dict[str, Any]`: The response from the `send_message` boto3 client method.
        """
        outputs = self.outputs()

        client = boto3.client("sqs")
        kwargs = {
            "QueueUrl": outputs.url,
            "MessageBody": message_body,
        }
        if delay_seconds:
            kwargs["DelaySeconds"] = str(delay_seconds)
        if message_attributes is not None:
            kwargs["MessageAttributes"] = message_attributes  # type: ignore
        if message_system_attributes is not None:
            kwargs["MessageSystemAttributes"] = message_system_attributes  # type: ignore
        if message_deduplication_id is not None:
            kwargs["MessageDeduplicationId"] = message_deduplication_id
        if message_group_id is not None:
            kwargs["MessageGroupId"] = message_group_id
        return client.send_message(**kwargs)  # type: ignore
