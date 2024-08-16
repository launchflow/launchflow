#
# Launchflow global variables
#
variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "env_role_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "launchflow_project" {
  type = string
}

variable "launchflow_environment" {
  type = string
}


#
# Code build project inputs
#

variable "build_timeout_minutes" {
  type    = number
  default = 30
}

variable "cache" {
  type = object({
    type     = string
    location = optional(string, null)
    modes    = optional(list(string), null)
  })
  default = null
}

variable "environment" {
  type = object({
    compute_type                = string
    image                       = string
    type                        = string
    image_pull_credentials_type = string
    privileged_mode             = bool
    environment_variables = optional(list(object({
      name  = string
      value = string
    })), null)
  })
}

variable "logs_config" {
  type = object({
    cloud_watch_logs = optional(object({
      status      = string
      group_name  = optional(string, null)
      stream_name = optional(string, null)
    }), null)
    s3_logs = optional(object({
      status   = string
      location = optional(string, null)
    }), null)
  })
  default = null
}

variable "build_source" {
  type = object({
    type           = string
    location       = optional(string, null)
    buildspec_path = optional(string, null)
  })
}
