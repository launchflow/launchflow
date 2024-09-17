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

variable "api_gateway_id" {
  type = string
}

variable "function_arn" {
  type = string
  default = null
}

variable "function_alias" {
  type = string
  default = null
}
