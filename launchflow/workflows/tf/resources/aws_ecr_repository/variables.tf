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
# ECR Specific variables
#

variable "force_delete" {
  type = bool
}

variable "image_tag_mutability" {
  type = string
}
