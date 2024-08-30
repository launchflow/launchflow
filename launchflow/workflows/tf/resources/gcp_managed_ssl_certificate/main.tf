provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = var.resource_id
  managed {
    domains = var.domains
  }
}

output "gcp_id" {
  value = google_compute_managed_ssl_certificate.default.id
}

output "domains" {
  value = google_compute_managed_ssl_certificate.default.managed[0].domains
}
