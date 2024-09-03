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

resource "kubernetes_deployment_v1" "default" {
  lifecycle {
    ignore_changes = [
      # These are handled by the deploy step
      spec[0].template[0].spec[0].container[0].image,
      spec[0].template[0].spec[0].container[0].env,
      spec[0].template[0].spec[0].service_account_name
    ]
  }
  metadata {
    name      = var.resource_id
    namespace = var.namespace
  }
  spec {
    replicas = var.num_replicas
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
          dynamic "resources" {
            for_each = var.container_resources != null ? [1] : []
            content {
              limits   = var.container_resources.limits
              requests = var.container_resources.requests
            }
          }
          dynamic "liveness_probe" {

            for_each = var.liveness_probe != null ? [1] : []
            content {
              http_get {
                path = var.liveness_probe.http_get.path
                port = var.liveness_probe.http_get.port
              }
              initial_delay_seconds = var.liveness_probe.initial_delay_seconds
              period_seconds        = var.liveness_probe.period_seconds
            }
          }

          dynamic "readiness_probe" {
            for_each = var.readiness_probe != null ? [1] : []
            content {
              http_get {
                path = var.readiness_probe.http_get.path
                port = var.readiness_probe.http_get.port
              }
              initial_delay_seconds = var.readiness_probe.initial_delay_seconds
              period_seconds        = var.readiness_probe.period_seconds
            }
          }

          dynamic "startup_probe" {
            for_each = var.startup_probe != null ? [1] : []
            content {
              http_get {
                path = var.startup_probe.http_get.path
                port = var.startup_probe.http_get.port
              }
              failure_threshold = var.startup_probe.failure_threshold
              period_seconds    = var.startup_probe.period_seconds
            }
          }
        }
        dynamic "toleration" {
          for_each = var.tolerations != null ? var.tolerations : []
          content {
            key      = toleration.value.key
            operator = toleration.value.operator
            value    = toleration.value.value
            effect   = toleration.value.effect
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "default" {
  metadata {
    name        = var.resource_id
    namespace   = var.namespace
    annotations = var.annotations
  }
  spec {
    selector = {
      app = var.resource_id
    }
    port {
      port        = 80
      target_port = var.container_port
    }
    type = var.service_type
  }

  wait_for_load_balancer = true
}

output "external_ip" {
  value       = try(kubernetes_service_v1.default.status[0].load_balancer[0].ingress[0].ip, null)
  description = "The external IP address of the Kubernetes service"
}

output "internal_ip" {
  value       = kubernetes_service_v1.default.spec.0.cluster_ip
  description = "The internal IP address (cluster IP) of the Kubernetes service"
}
