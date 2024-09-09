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
# GCP autoscaler configuration
#
variable "instance_group_manager_id" {
  type = string
}

variable "region" {
  type = string
}

variable "autoscaling_policies" {
  type = list(object({
    max_replicas    = number
    min_replicas    = number
    cooldown_period = optional(number, null)
    cpu_utilization = optional(object(
      {
        target            = number
        predictive_method = string
      }
    ), null)
    custom_metric = optional(object(
      {
        name   = string
        target = optional(number, null)
        type   = optional(string, null)
      }
    ), null)
    load_balancing_utilization = optional(object(
      {
        target = number
      }
    ), null)
  }))
}
