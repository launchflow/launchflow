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
# Redis specific variables
#
variable "redis_tier" {
  type = string
}

variable "redis_version" {
  type = string
}

variable "memory_size_gb" {
  type = number
}

variable "enable_tls" {
  type = bool
}
