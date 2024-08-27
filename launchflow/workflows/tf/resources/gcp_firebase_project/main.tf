provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enables required APIs.
resource "google_project_service" "default" {
  provider = google
  project  = var.gcp_project_id
  for_each = toset([
    "firebase.googleapis.com",
  ])
  service = each.key

  # Don't disable the service if the resource block is removed by accident.
  disable_on_destroy = false
}

# Enables Firebase services for the new project created above.
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.gcp_project_id

  # Waits for the required APIs to be enabled.
  depends_on = [
    google_project_service.default
  ]
}

output "gcp_id" {
  value = google_firebase_project.default.id
}
