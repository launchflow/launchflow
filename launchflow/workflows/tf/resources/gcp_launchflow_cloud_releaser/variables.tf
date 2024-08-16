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

variable "launchflow_service_account" {
  type = string
}

#
# Launchflow cloud releaser specific variables
#

variable "permissions" {
  type = list(string)
}
