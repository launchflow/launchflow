variable "gcp_project_id" {
  type = string
}

# Resource information
variable "environment_service_account_email" {
  type = string
}

variable "enable_vpc_connection" {
  type = bool
}

variable "artifact_bucket" {
  type = string
}
