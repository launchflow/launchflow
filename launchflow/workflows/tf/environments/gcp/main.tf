provider "google" {
  project = var.gcp_project_id
}

provider "google-beta" {
  project = var.gcp_project_id
}

locals {
  roles = [
    # Cloud SQL roles need to be at the project level
    "roles/cloudsql.admin",
    "roles/cloudsql.client",
    # Memorystore roles need to be at the project level
    "roles/redis.admin",
    # BigQuery roles need to be at the project level
    "roles/bigquery.user",
    # Metrics and Logs writer role allows writing logs from compute engine
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",

  ]
  # We enable common apis to speed up individual resource creation
  services = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "storage-component.googleapis.com",
    "compute.googleapis.com",
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "servicenetworking.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
  ]

  env_service_account_id = "projects/${var.gcp_project_id}/serviceAccounts/${var.environment_service_account_email}"
}

resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = var.artifact_bucket
  role   = "roles/storage.admin"
  member = "serviceAccount:${var.environment_service_account_email}"
}

resource "google_project_service" "environment_services" {
  for_each = toset(local.services)

  project            = var.gcp_project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_project_iam_member" "service_account_roles" {
  for_each = toset(local.roles)

  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${var.environment_service_account_email}"
}

resource "google_service_account_iam_member" "env-account-iam" {
  service_account_id = local.env_service_account_id
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${var.environment_service_account_email}"
}

resource "google_service_account_iam_member" "env-account-iam-self" {
  service_account_id = local.env_service_account_id
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.environment_service_account_email}"
}

data "google_compute_network" "default_private_network" {
  depends_on = [google_project_service.environment_services]
  name       = "default"
}

resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_vpc_connection ? 1 : 0
  provider      = google-beta
  project       = var.gcp_project_id
  name          = "google-networkd-connection-ips"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = data.google_compute_network.default_private_network.id
  depends_on    = [google_project_service.environment_services]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_vpc_connection ? 1 : 0
  provider                = google-beta
  depends_on              = [google_project_service.environment_services]
  network                 = data.google_compute_network.default_private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]
}
