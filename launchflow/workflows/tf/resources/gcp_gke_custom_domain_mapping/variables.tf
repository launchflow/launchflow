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

variable "cluster_id" {
  type = string
}

variable "namespace" {
  type = string
}

variable "service_name" {
  type = string
}

variable "port" {
  type = string
}
