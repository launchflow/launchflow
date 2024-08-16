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
# Health check tofu variables
#
variable "check_interval_sec" {
  type = number
}

variable "timeout_sec" {
  type = number
}

variable "healthy_threshold" {
  type = number
}

variable "unhealthy_threshold" {
  type = number
}

variable "host" {
  type    = string
  default = null
}

variable "request_path" {
  type = string
}

variable "port" {
  type = string
}

variable "response" {
  type    = string
  default = null
}

variable "proxy_header" {
  type    = string
  default = null
}

variable "port_specification" {
  type    = string
  default = null
}
