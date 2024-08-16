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
# GCP allow rule firewall configuration
#
variable "direction" {
  type = string
}

variable "priority" {
  type = number
}

variable "source_ranges" {
  type    = list(string)
  default = null
}

variable "source_tags" {
  type    = list(string)
  default = null
}

variable "target_tags" {
  type    = list(string)
  default = null
}

variable "target_service_accounts" {
  type    = list(string)
  default = null
}

variable "description" {
  type    = string
  default = null
}

variable "allow_rules" {
  type = list(object({
    protocol = string
    ports    = list(string)
  }))
  default = null
}

variable "destination_ranges" {
  type    = list(string)
  default = null
}
