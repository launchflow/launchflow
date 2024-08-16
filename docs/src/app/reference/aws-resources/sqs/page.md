## SQSQueue

A queue in AWS's SQS service.

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

### initialization

Create a new SQS queue resource.

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

### send\_message

```python
SQSQueue.send_message(message_body: str, delay_seconds: int = 0, message_attributes: Optional[Dict[str, Any]] = None, message_system_attributes: Optional[Dict[str, Any]] = None, message_deduplication_id: Optional[str] = None, message_group_id: Optional[str] = None) -> Dict[str, Any]
```

Send a message to the queue using the boto3 client library.

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
