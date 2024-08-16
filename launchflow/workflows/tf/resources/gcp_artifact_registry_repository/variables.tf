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

variable "environment_service_account_email" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

#
# Artifact registry specific variables
#

variable "location" {
  type     = string
  nullable = true
  default  = null
}

variable "format" {
  type = string
}
