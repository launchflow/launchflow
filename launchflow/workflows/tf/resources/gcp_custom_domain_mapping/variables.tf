#
# LaunchFlow global tofu variables
#
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

#
# Custom domain mapping specific fields
#
variable "ip_address_id" {
  type = string
}

variable "ssl_certificate_id" {
  type = string
}

variable "cloud_run_service" {
  type    = string
  default = null
}

variable "gce_service" {
  type    = string
  default = null
}

variable "region" {
  type    = string
  default = null
}

variable "health_check" {
  type    = string
  default = null
}

variable "named_port" {
  type    = string
  default = null
}

variable "include_http_redirect" {
  type    = bool
  default = true
}
