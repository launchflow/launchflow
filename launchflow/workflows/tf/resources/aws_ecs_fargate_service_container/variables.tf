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
# ECS Fargate service container specific variables
#

variable "ecs_cluster_name" {
  type = string
}

variable "resource_name" {
  type = string
}

variable "port" {
  type = number
}

variable "desired_count" {
  type = number
}

variable "alb_security_group_id" {
  type    = string
  default = null
}

variable "alb_target_group_arn" {
  type = string
}
