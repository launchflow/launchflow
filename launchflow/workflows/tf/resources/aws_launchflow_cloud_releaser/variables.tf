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

variable "launchflow_project" {
  type = string
}

variable "launchflow_environment" {
  type = string
}

variable "env_role_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

#
# Launchflow cloud releaser specific variables
#

variable "launchflow_cloud_aws_account_id" {
  type = string
}

variable "launchflow_cloud_role_name" {
  type = string
}

variable "launchflow_cloud_external_role_id" {
  type = string
}

variable "environment_allowed_actions" {
  type = list(string)
}

variable "account_allowed_actions" {
  type = list(string)
}
