provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_compute_health_check" "default" {
  name                = var.resource_id
  check_interval_sec  = var.check_interval_sec
  timeout_sec         = var.timeout_sec
  healthy_threshold   = var.healthy_threshold
  unhealthy_threshold = var.unhealthy_threshold

  http_health_check {
    port               = var.port
    request_path       = var.request_path
    response           = var.response
    proxy_header       = var.proxy_header
    port_specification = var.port_specification
  }
}

output "gcp_id" {
  value = google_compute_health_check.default.id
}
