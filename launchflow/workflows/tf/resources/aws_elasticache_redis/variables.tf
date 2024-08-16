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
# Elasticache Redis variables
#
variable "node_type" {
  type = string
}

variable "parameter_group_name" {
  type = string
}

variable "engine_version" {
  type = string
}
