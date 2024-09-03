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

variable "custom_domain" {
  type    = string
  default = null
}

variable "main_page_suffix" {
  type    = string
  default = "index.html"
}

variable "not_found_page" {
  type    = string
  default = "index.html"
}
