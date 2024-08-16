#
# LaunchFlow global tofu variables
#
variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "environment_service_account_email" {
  type = string
}

#
# Pub/Sub Subscription specific variables
#
variable "topic" {
  type = string
}

variable "ack_deadline_seconds" {
  type     = number
  nullable = true
  default  = null
}

variable "retain_acked_messages" {
  type     = bool
  nullable = true
  default  = null
}

variable "message_retention_duration" {
  type     = string
  nullable = true
  default  = null
}

variable "filter" {
  type     = string
  nullable = true
  default  = null
}

variable "push_config" {
  type = object({
    push_endpoint = string
    attributes    = map(string)
    oidc_token = object({
      service_account_email = string
      audience              = string
    })
  })
  nullable = true
  default  = null
}
