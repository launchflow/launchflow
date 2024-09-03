variable "resource_id" {
  type = string
}

variable "cluster_id" {
  type = string
}

variable "k8_provider" {
  type = string
}

variable "namespace" {
  type = string
}

variable "max_replicas" {
  type = number
}

variable "min_replicas" {
  type = number
}

variable "target_name" {
  type = string
}

variable "resource_metrics" {
  type = list(object({
    name                       = string
    target_type                = string
    target_average_value       = optional(number, null)
    target_average_utilization = optional(number, null)
    target_value               = optional(number, null)
  }))
}
