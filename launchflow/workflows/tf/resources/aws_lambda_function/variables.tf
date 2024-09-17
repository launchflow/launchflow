#
# LaunchFlow global tofu variables
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
# Lambda service container specific variables
#

variable "timeout_seconds" {
  type = number
}

variable "memory_size_mb" {
  type = number
}

variable "package_type" {
  type = string
}

variable "runtime" {
  type = string
  default = null
}

variable "image_uri" {
  type = string
  default = null
}
