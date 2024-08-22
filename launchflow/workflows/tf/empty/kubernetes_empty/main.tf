locals {
  cluster          = var.k8_provider == "gke" ? data.google_container_cluster.default[0] : null
  kube_config      = var.k8_provider == "gke" ? data.google_client_config.default[0] : null
  gke_project_name = var.k8_provider == "gke" ? split("/", var.cluster_id)[1] : null
  gke_location     = var.k8_provider == "gke" ? split("/", var.cluster_id)[3] : null
  gke_cluster_name = var.k8_provider == "gke" ? split("/", var.cluster_id)[5] : null
}

data "google_container_cluster" "default" {
  count    = var.k8_provider == "gke" ? 1 : 0
  name     = local.gke_cluster_name
  location = local.gke_location
  project  = local.gke_project_name
}

data "google_client_config" "default" {
  count = var.k8_provider == "gke" ? 1 : 0
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
