provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

locals {
  password = var.password == null ? random_password.user-password[0].result : var.password
}


resource "random_password" "user-password" {
  count   = var.password == null ? 1 : 0
  length  = 16
  special = true
}

resource "google_sql_user" "cloud_sql_user" {
  name     = var.resource_id
  instance = var.cloud_sql_instance
  password = local.password
  project  = var.gcp_project_id
  # NOTE: We use the ABANDON deletion policy since Postgres databases not owned by the
  # cloudsqlsuperuser cannot be deleted by the API
  deletion_policy = "ABANDON"
}

output "user" {
  description = "The user name for the database."
  value       = google_sql_user.cloud_sql_user.name
}

output "password" {
  description = "The auto-generated default user password if no input password was provided"
  value       = local.password
  sensitive   = true
}

output "gcp_id" {
  value = google_sql_user.cloud_sql_user.id
}
