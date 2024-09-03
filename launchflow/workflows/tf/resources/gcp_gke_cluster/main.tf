provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_project_service" "container_service" {
  service = "container.googleapis.com"

  disable_on_destroy = false

}

data "google_compute_network" "default" {
  name = "default"
}



resource "google_compute_subnetwork" "k8_subnetwork" {
  name          = "${var.resource_id}-sub-network"
  network       = data.google_compute_network.default.self_link
  ip_cidr_range = var.subnet_ip_cidr_range

  secondary_ip_range {
    range_name    = "pods-range"
    ip_cidr_range = var.pod_ip_cidr_range
  }

  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = var.service_ip_cidr_range
  }
}

module "gke" {
  depends_on = [google_project_service.container_service]
  source     = "terraform-google-modules/kubernetes-engine/google"
  project_id = var.gcp_project_id
  name       = var.resource_id
  region     = var.region
  regional   = var.regional
  zones      = var.zones
  # TODO: allow these to be configured
  network                         = "default"
  subnetwork                      = google_compute_subnetwork.k8_subnetwork.name
  ip_range_pods                   = "pods-range"
  ip_range_services               = "services-range"
  enable_vertical_pod_autoscaling = true
  create_service_account          = false
  service_account                 = var.environment_service_account_email
  deletion_protection             = var.delete_protection
}



output "gcp_id" {
  value = module.gke.cluster_id
}

data "google_client_config" "default" {}


provider "kubernetes" {
  host                   = "https://${module.gke.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke.ca_certificate)

  ignore_annotations = [
    "^autopilot\\.gke\\.io\\/.*",
    "^cloud\\.google\\.com\\/.*"
  ]
}

data "google_service_account" "default" {
  account_id = split("@", var.environment_service_account_email)[0]
}

resource "kubernetes_service_account" "default" {
  depends_on = [module.gke]
  metadata {
    name = split("@", var.environment_service_account_email)[0]
    annotations = {
      "iam.gke.io/gcp-service-account" = data.google_service_account.default.email
    }
  }
}

resource "google_service_account_iam_member" "default" {
  service_account_id = data.google_service_account.default.id
  member             = "serviceAccount:${var.gcp_project_id}.svc.id.goog[${kubernetes_service_account.default.id}]"

  role = "roles/iam.workloadIdentityUser"
}
