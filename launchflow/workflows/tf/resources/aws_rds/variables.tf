#
# LaunchFlow global variables
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

variable "vpc_id" {
  type = string
}

variable "env_role_name" {
  type = string
}

#
# RDS specific variables
#
variable "database_name" {
  type = string
}

variable "publicly_accessible" {
  type = bool
}

variable "instance_class" {
  type = string
}

variable "allocated_storage_gb" {
  type = number
}

variable "highly_available" {
  type = bool
}

variable "engine" {
  type = string
}

variable "engine_version" {
  type = string
}

variable "engine_family" {
  type = string
}
