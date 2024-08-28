provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


# HTTPS Load Balancer setup
resource "google_compute_global_forwarding_rule" "default" {
  name                  = "${var.resource_id}-forwarding-rule"
  target                = google_compute_target_https_proxy.default.id
  port_range            = "443"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = var.ip_address_id
}

resource "google_compute_target_https_proxy" "default" {
  name             = "${var.resource_id}-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [var.ssl_certificate_id]
}


resource "google_compute_url_map" "default" {
  name = var.resource_id

  default_service = google_compute_backend_service.default.self_link
}


locals {
  backend_group = var.cloud_run_service == null ? data.google_compute_region_instance_group.default[0].self_link : google_compute_region_network_endpoint_group.cloud_run_neg[0].self_link
  split         = var.cloud_run_service == null ? split("/", var.gce_service) : split("/", var.cloud_run_service)
  resource_id   = element(local.split, length(local.split) - 1)
}

resource "google_compute_backend_service" "default" {
  name                  = "${var.resource_id}-backend-service"
  protocol              = var.cloud_run_service == null ? "HTTP" : "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  health_checks = var.health_check == null ? null : [
    var.health_check
  ]
  port_name = var.named_port == null ? null : var.named_port
  backend {
    group = local.backend_group

  }
}

data "google_compute_region_instance_group" "default" {
  count  = var.gce_service == null ? 0 : 1
  name   = local.resource_id
  region = var.region
}

resource "google_compute_region_network_endpoint_group" "cloud_run_neg" {
  count                 = var.cloud_run_service == null ? 0 : 1
  name                  = "${local.resource_id}-serverless-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region == null ? var.gcp_region : var.region
  cloud_run {
    service = local.resource_id
  }
}

# HTTP Proxy setup
resource "google_compute_global_forwarding_rule" "http" {
  count                 = var.include_http_redirect ? 1 : 0
  name                  = "${var.resource_id}-http-forwarding-rule"
  target                = google_compute_target_http_proxy.default[0].id
  port_range            = "80"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  description           = "Forwarding rule for HTTP -> HTTPS redirect for ${var.resource_id}"
  ip_address            = var.ip_address_id
}

resource "google_compute_target_http_proxy" "default" {
  count   = var.include_http_redirect ? 1 : 0
  name    = "${var.resource_id}-http-proxy"
  url_map = google_compute_url_map.http_redirect[0].id
}

resource "google_compute_url_map" "http_redirect" {
  count = var.include_http_redirect ? 1 : 0
  name  = "${var.resource_id}-http-redirect"

  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
}


output "gcp_id" {
  value = google_compute_url_map.default.id
}
