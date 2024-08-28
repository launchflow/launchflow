provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_compute_global_address" "default" {
  name = var.resource_id
}

output "gcp_id" {
  value = google_compute_global_address.default.id
}

output "ip_address" {
  value = google_compute_global_address.default.address
}
