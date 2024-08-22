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
  node_pool_name   = var.k8_provider == "gke" && var.node_pool_id != null ? split("/", var.node_pool_id)[7] : null
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

# TODO: add life cycle ignore aroud the container and anything else we change in the update flow
resource "kubernetes_deployment_v1" "default" {
  metadata {
    name      = var.resource_id
    namespace = var.namespace
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = var.resource_id
      }
    }
    template {
      metadata {
        labels = {
          app = var.resource_id
        }
      }
      spec {
        node_selector = {
          "nodepool" = local.node_pool_name
        }
        container {
          image = var.image
          name  = var.resource_id
          port {
            container_port = var.container_port
            host_port      = var.host_port

          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "default" {
  metadata {
    name      = var.resource_id
    namespace = var.namespace
  }
  spec {
    selector = {
      app = var.resource_id
    }
    port {
      port        = var.host_port
      target_port = var.host_port
    }
    type = "LoadBalancer"
  }
}

output "external_ip" {
  value       = length(kubernetes_service_v1.default.status) > 0 ? kubernetes_service_v1.default.status.0.load_balancer.0.ingress.0.ip : null
  description = "The external IP address of the Kubernetes service"
}

output "internal_ip" {
  value       = kubernetes_service_v1.default.spec.0.cluster_ip
  description = "The internal IP address (cluster IP) of the Kubernetes service"
}
