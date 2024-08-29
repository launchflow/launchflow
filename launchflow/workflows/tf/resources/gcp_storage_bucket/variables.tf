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
# GCS Bucket specific variables
#

variable "location" {
  type = string
}

variable "force_destroy" {
  type    = bool
  default = false
}

variable "uniform_bucket_level_access" {
  type    = bool
  default = false
}
