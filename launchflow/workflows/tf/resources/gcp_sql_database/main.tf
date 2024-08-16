provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_sql_database" "cloud_sql_database" {
  name     = var.resource_id
  instance = var.cloud_sql_instance
  project  = var.gcp_project_id
}

output "database_name" {
  value = google_sql_database.cloud_sql_database.name
}
