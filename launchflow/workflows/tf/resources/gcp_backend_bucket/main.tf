provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_storage_bucket" "bucket" {
  name                        = var.resource_id
  project                     = var.gcp_project_id
  location                    = var.location
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  website {
    main_page_suffix = var.main_page_suffix
    not_found_page   = var.not_found_page
  }
}

resource "google_storage_bucket_object" "index_html" {
  name         = var.main_page_suffix
  bucket       = google_storage_bucket.bucket.name
  content      = <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>Hello World!</title>
  </head>
  <body>
    <h1>Hello World!</h1>
    <p>This is a basic HTML page served from Google Cloud Storage.</p>
  </body>
</html>
EOF
  content_type = "text/html"
}

resource "google_compute_global_address" "default" {
  name = "${var.resource_id}-ip"
}

resource "google_compute_managed_ssl_certificate" "custom_domain_cert" {
  count = var.custom_domain == null ? 0 : 1
  name  = "${var.resource_id}-ssl-cert"
  managed {
    domains = [var.custom_domain]
  }
}

resource "google_compute_backend_bucket" "default" {
  name        = var.resource_id
  description = "Contains beautiful images"
  bucket_name = google_storage_bucket.bucket.name
  enable_cdn  = true
}

resource "google_compute_url_map" "default" {
  name            = "${var.resource_id}-url-map"
  default_service = google_compute_backend_bucket.default.id
}

resource "google_compute_target_http_proxy" "default_http" {
  count   = var.custom_domain == null ? 1 : 0
  name    = "${var.resource_id}-http-proxy"
  url_map = google_compute_url_map.default.id
}

resource "google_compute_target_https_proxy" "default_https" {
  count            = var.custom_domain == null ? 0 : 1
  name             = "${var.resource_id}-https-proxy"
  ssl_certificates = [google_compute_managed_ssl_certificate.custom_domain_cert[0].id]
  url_map          = google_compute_url_map.default.id
}

resource "google_compute_global_forwarding_rule" "http" {
  count                 = var.custom_domain == null ? 1 : 0
  name                  = "${var.resource_id}-http-forwarding-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "80"
  target                = google_compute_target_http_proxy.default_http[0].id
  ip_address            = google_compute_global_address.default.id
}

resource "google_compute_global_forwarding_rule" "https" {
  count                 = var.custom_domain == null ? 0 : 1
  name                  = "${var.resource_id}-https-forwarding-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443"
  target                = google_compute_target_https_proxy.default_https[0].id
  ip_address            = google_compute_global_address.default.id
}

output "bucket_name" {
  value = google_storage_bucket.bucket.name
}

output "cdn_ip_address" {
  value       = google_compute_global_address.default.address
  description = "IP address to configure in your DNS for pointing to the Google Cloud CDN."
}

output "url_map_resource_id" {
  value = google_compute_url_map.default.id
}

output "gcp_id" {
  value = google_storage_bucket.bucket.id
}
