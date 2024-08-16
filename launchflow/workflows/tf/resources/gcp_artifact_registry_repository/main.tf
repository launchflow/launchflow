provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_artifact_registry_repository" "repository" {
  repository_id = var.resource_id
  location      = var.location != null ? var.location : var.gcp_region
  format        = var.format
  # TODO: add additional configuration
}

resource "google_artifact_registry_repository_iam_member" "env_service_account_admin_permissions" {
  project    = google_artifact_registry_repository.repository.project
  location   = google_artifact_registry_repository.repository.location
  repository = google_artifact_registry_repository.repository.name

  role   = "roles/artifactregistry.admin"
  member = "serviceAccount:${var.environment_service_account_email}"

  depends_on = [
    google_artifact_registry_repository.repository
  ]
}

locals {
  docker_repository = var.format == "DOCKER" ? "${google_artifact_registry_repository.repository.location}-docker.pkg.dev/${google_artifact_registry_repository.repository.project}/${google_artifact_registry_repository.repository.repository_id}" : null
}


output "docker_repository" {
  value = local.docker_repository
}

output "gcp_id" {
  value = google_artifact_registry_repository.repository.id
}
