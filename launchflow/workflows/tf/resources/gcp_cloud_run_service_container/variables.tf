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
# Cloud run container specific variables
#

variable "region" {
  type    = string
  default = null
}

variable "launchflow_project" {
  type = string
}

variable "launchflow_environment" {
  type = string
}

variable "cpu" {
  type     = number
  default  = null
  nullable = true
}

variable "memory" {
  type     = string
  default  = null
  nullable = true
}

variable "port" {
  type     = number
  default  = null
  nullable = true
}

variable "publicly_accessible" {
  type    = bool
  default = true
}

variable "min_instance_count" {
  type     = number
  default  = null
  nullable = true
}

variable "max_instance_count" {
  type     = number
  default  = null
  nullable = true
}

variable "max_instance_request_concurrency" {
  type     = number
  default  = null
  nullable = true
}

variable "invokers" {
  type    = list(string)
  default = []
}

variable "custom_audiences" {
  type    = list(string)
  default = []
}

variable "ingress" {
  type     = string
  default  = null
  nullable = true
}

variable "environment_variables" {
  type    = map(string)
  default = null
}
