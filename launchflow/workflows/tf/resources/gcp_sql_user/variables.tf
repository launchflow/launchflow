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
# User specific variables
#

variable "password" {
  type     = string
  nullable = true
  default  = null
}

variable "cloud_sql_instance" {
  type = string
}
