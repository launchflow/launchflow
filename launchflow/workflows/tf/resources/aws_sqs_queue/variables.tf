#
# Launchflow global variables
#
variable "aws_account_id" {
  type = string
}
variable "aws_region" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "launchflow_project" {
  type = string
}

variable "launchflow_environment" {
  type = string
}

variable "env_role_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

#
# SQS Queue specific variables
#

variable "delivery_delay_seconds" {
  type = number
}

variable "max_message_size_bytes" {
  type = number
}

variable "message_retention_period_seconds" {
  type = number
}

variable "receive_wait_time_seconds" {
  type = number
}

variable "visibility_timeout_seconds" {
  type = number
}

variable "fifo_queue" {
  type = bool
}

variable "content_based_deduplication" {
  type = bool
}

variable "deduplication_scope" {
  type    = string
  default = null
}

variable "fifo_throughput_limit" {
  type    = string
  default = null
}
