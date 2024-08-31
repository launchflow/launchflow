locals {
  cluster          = data.google_container_cluster.default
  kube_config      = data.google_client_config.default
  gke_project_name = split("/", var.cluster_id)[1]
  gke_location     = split("/", var.cluster_id)[3]
  gke_cluster_name = split("/", var.cluster_id)[5]

  split_ip_address_id = split("/", var.ip_address_id)
  ip_address_name     = element(local.split_ip_address_id, length(local.split_ip_address_id) - 1)

  split_ssl_certificate_id = split("/", var.ssl_certificate_id)
  ssl_certificate_name     = element(local.split_ssl_certificate_id, length(local.split_ssl_certificate_id) - 1)
}

data "google_client_config" "default" {
}

data "google_container_cluster" "default" {
  name     = local.gke_cluster_name
  location = local.gke_location
  project  = local.gke_project_name
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

resource "kubernetes_ingress_v1" "default" {
  metadata {
    name      = var.resource_id
    namespace = var.namespace
    annotations = {
      "kubernetes.io/ingress.global-static-ip-name" : local.ip_address_name
      "ingress.gcp.kubernetes.io/pre-shared-cert" = local.ssl_certificate_name
    }
  }
  spec {
    default_backend {
      service {
        name = var.service_name
        port {
          number = var.port
        }
      }
    }
  }
  wait_for_load_balancer = true
}

# TODO: figure out how to get the gcp id of the load balancer
