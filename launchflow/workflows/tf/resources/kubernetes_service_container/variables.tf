variable "resource_id" {
  type = string
}

variable "cluster_id" {
  type = string
}

variable "k8_provider" {
  type = string
}

variable "container_port" {
  type = number
}

variable "host_port" {
  type    = number
  default = null
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
variable "liveness_probe" {
  type = object({
    http_get = object({
      path = string
      port = number
    })
    initial_delay_seconds = number
    period_seconds        = number
  })
  default = null
}
variable "readiness_probe" {
  type = object({
    http_get = object({
      path = string
      port = number
    })
    initial_delay_seconds = number
    period_seconds        = number
  })
  default = null
}

variable "startup_probe" {
  type = object({
    http_get = object({
      path = string
      port = number
    })
    failure_threshold = number
    period_seconds    = number
  })
  default = null
}

variable "service_type" {
  type = string
}

variable "num_replicas" {
  type = string
}
