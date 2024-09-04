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
# NAT Gateway tofu variables
#

variable "eip_allocation_id" {
  type = string
}

variable "private_route_config" {
  type = object({
    destination_cidr_block = string
  })
  default = null
}
