#
# LaunchFlow global tofu variables
#
variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "environment_service_account_email" {
  type = string
}

#
# Managed instance group tofu variables
#

variable "base_instance_name" {
  type = string
}

variable "target_size" {
  type    = number
  default = null
}

variable "region" {
  type = string
}

variable "update_policy" {
  type = object({
    type                           = string
    minimal_action                 = string
    most_disruptive_allowed_action = optional(string, null)
    instance_redistribution_type   = optional(string, null)
    max_surge_fixed                = optional(number, null)
    max_surge_percentage           = optional(number, null)
    max_unavailable_fixed          = optional(number, null)
    max_unavailable_percentage     = optional(number, null)
    replacement_method             = optional(string, null)
    min_ready_sec                  = optional(number, null)
  })
}

variable "auto_healing_policy" {
  type = object({
    health_check      = string
    initial_delay_sec = number
  })
  default = null
}

variable "named_ports" {
  type = list(object({
    name = string
    port = number
  }))
  default = null
}
