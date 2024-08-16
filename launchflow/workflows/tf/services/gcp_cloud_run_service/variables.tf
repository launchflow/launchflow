variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "docker_image" {
  type = string
}

variable "launchflow_project" {
  type = string
}

variable "launchflow_environment" {
  type = string
}

variable "service_name" {
  type = string
}

variable "launchflow_deployment_id" {
  type = string
}

variable "environment_service_account" {
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
