data "google_client_config" "default" {
  count = var.k8_provider == "gke" ? 1 : 0
}

data "google_container_cluster" "default" {
  count    = var.k8_provider == "gke" ? 1 : 0
  name     = local.gke_cluster_name
  location = local.gke_location
  project  = local.gke_project_name
}

locals {
  cluster          = var.k8_provider == "gke" ? data.google_container_cluster.default[0] : null
  kube_config      = var.k8_provider == "gke" ? data.google_client_config.default[0] : null
  gke_project_name = var.k8_provider == "gke" ? split("/", var.cluster_id)[1] : null
  gke_location     = var.k8_provider == "gke" ? split("/", var.cluster_id)[3] : null
  gke_cluster_name = var.k8_provider == "gke" ? split("/", var.cluster_id)[5] : null
}

provider "kubernetes" {
  host                   = "https://${local.cluster.endpoint}"
  token                  = local.kube_config.access_token
  cluster_ca_certificate = base64decode(local.cluster.master_auth[0].cluster_ca_certificate)

  ignore_annotations = [
    "^autopilot\\.gke\\.io\\/.*",
    "^cloud\\.google\\.com\\/.*"
  ]
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "default" {
  metadata {
    name      = var.resource_id
    namespace = var.namespace
  }
  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = var.target_name
    }
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    dynamic "metric" {
      for_each = var.resource_metrics
      content {
        type = "Resource"
        resource {
          name = metric.value.name
          target {
            type                = metric.value.target_type
            average_value       = metric.value.target_average_value
            average_utilization = metric.value.target_average_utilization
            value               = metric.value.target_value
          }
        }
      }
    }
  }
}
