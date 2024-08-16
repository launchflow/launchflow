variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "service_name" {
  type = string
}

variable "docker_image" {
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

variable "launchflow_deployment_id" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "ecs_cluster_name" {
  type = string
}

variable "launchflow_env_role_name" {
  type = string
}
