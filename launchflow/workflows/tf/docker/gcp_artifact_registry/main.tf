provider "google" {
  project      = var.gcp_project_id
}

# Create an artifact registry repository for the service
resource "google_artifact_registry_repository" "docker_repository" {
  location      = var.gcp_region
  repository_id = var.repository_name
  format        = "DOCKER"
}

output "docker_repository" {
  value = "${google_artifact_registry_repository.docker_repository.location}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker_repository.repository_id}"
}
