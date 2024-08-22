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
