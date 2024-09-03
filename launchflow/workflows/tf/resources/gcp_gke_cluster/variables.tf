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
# GKE Cluster tofu variables
#
variable "delete_protection" {
  type = bool
}

variable "subnet_ip_cidr_range" {
  type = string
}

variable "pod_ip_cidr_range" {
  type = string
}

variable "service_ip_cidr_range" {
  type = string
}

variable "region" {
  type = string
}

variable "zones" {
  type    = list(string)
  default = []
}

variable "regional" {
  type = bool
}
