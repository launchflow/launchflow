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
# EC2 specific variables
#
variable "instance_type" {
  type = string
}

variable "disk_size_gb" {
  type = number
}

variable "additional_outputs" {
  type = map(string)
}

variable "docker_cfg" {
  type = object({
    image                 = string
    args                  = list(string)
    environment_variables = map(string)
  })
}

variable "firewall_cfg" {
  type = object({
    expose_ports = list(number)
  })
}

variable "associate_public_ip_address" {
  type = bool
}

variable "publicly_accessible" {
  type = bool
}
