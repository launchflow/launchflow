provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_project_service" "redis_service" {
  project            = var.gcp_project_id
  service            = "redis.googleapis.com"
  disable_on_destroy = false

}

resource "google_redis_instance" "cache" {
  name                    = var.resource_id
  project                 = var.gcp_project_id
  region                  = var.gcp_region
  memory_size_gb          = var.memory_size_gb
  tier                    = var.redis_tier
  redis_version           = var.redis_version
  transit_encryption_mode = var.enable_tls ? "SERVER_AUTHENTICATION" : "DISABLED"

  auth_enabled = true

  lifecycle {
    prevent_destroy = false
  }

  depends_on = [google_project_service.redis_service]
}

output "host" {
  description = "The IP address of the instance."
  value       = google_redis_instance.cache.host
}

output "port" {
  description = "The port number of the exposed Redis endpoint."
  value       = google_redis_instance.cache.port
}

output "password" {
  description = "AUTH String set on the instance. This field will only be populated if auth_enabled is true."
  value       = google_redis_instance.cache.auth_string
  sensitive   = true
}

output "gcp_id" {
  value = google_redis_instance.cache.id
}
