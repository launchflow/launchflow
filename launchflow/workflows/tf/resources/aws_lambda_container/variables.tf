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

variable "timeout" {
  type = number
}

variable "memory_size" {
  type = number
}

variable "package_type" {
  type = string
}

variable "runtime" {
  type = string
}

variable "port" {
  type = number
}

variable "setup_api_gateway" {
  type = bool
}