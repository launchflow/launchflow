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
# GKE node pool tofu variables
#
variable "cluster_id" {
  type = string
}

variable "preemptible" {
  type = bool
}

variable "machine_type" {
  type = string
}

variable "autoscaling" {
  type = object({
    min_node_count       = optional(number, null)
    max_node_count       = optional(number, null)
    total_min_node_count = optional(number, null)
    total_max_node_count = optional(number, null)
    location_policy      = optional(string, null)
  })

  default = null
}

variable "disk_size_gb" {
  type    = number
  default = null
}

variable "disk_type" {
  type    = string
  default = null
}

variable "image_type" {
  type    = string
  default = null
}

variable "guest_accelerators" {
  type = list(object({
    type  = string
    count = number
  }))
  default = null
}
