variable "resource_id" {
  type = string
}

variable "cluster_id" {
  type = string
}

variable "k8_provider" {
  type = string
  validation {
    condition     = contains(["gke", "eks"], var.k8_provider)
    error_message = "Allowed values for provider are \"gke\" or \"eks\"."
  }
}

variable "container_port" {
  type = number
}

variable "host_port" {
  type = number
}

variable "node_pool_id" {
  type    = string
  default = null
}

variable "namespace" {
  type = string
}

variable "image" {
  type = string
}
