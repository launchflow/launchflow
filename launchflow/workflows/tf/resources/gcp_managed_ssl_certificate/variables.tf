variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "environment_service_account_email" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "domains" {
  type = list(string)
}
