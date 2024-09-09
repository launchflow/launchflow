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
# Application Load Balancer specific variables
#

variable "container_port" {
  type = number
}

variable "health_check_path" {
  type    = string
  default = null
}


variable "domain_name" {
  type    = string
  default = null
}
