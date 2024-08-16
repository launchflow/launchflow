provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region              = var.aws_region
}

resource "aws_sqs_queue" "queue" {
  name                        = var.resource_id
  delay_seconds               = var.delivery_delay_seconds
  max_message_size            = var.max_message_size_bytes
  message_retention_seconds   = var.message_retention_period_seconds
  receive_wait_time_seconds   = var.receive_wait_time_seconds
  visibility_timeout_seconds  = var.visibility_timeout_seconds
  fifo_queue                  = var.fifo_queue
  deduplication_scope         = var.deduplication_scope
  content_based_deduplication = var.content_based_deduplication
  fifo_throughput_limit       = var.fifo_throughput_limit
}

output "url" {
  value = aws_sqs_queue.queue.url
}

output "aws_arn" {
  value = aws_sqs_queue.queue.arn
}
