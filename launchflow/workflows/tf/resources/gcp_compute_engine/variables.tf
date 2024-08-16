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
# GCP compute engine specific variables
#

variable "machine_type" {
  type = string
}

variable "additional_outputs" {
  type = map(string)
}

variable "docker_cfg" {
  type = object({
    image                 = string
    args                  = list(string)
    environment_variables = list(map(string))
  })
}

variable "firewall_cfg" {
  type = object({
    expose_ports = list(number)
  })
}

variable "service_account_email" {
  type    = string
  default = null
}
