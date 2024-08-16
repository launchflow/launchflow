provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_bigquery_dataset_iam_member" "dataset_iam" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  role       = "roles/bigquery.admin"
  member     = "serviceAccount:${var.environment_service_account_email}"
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = var.resource_id
  location                   = var.location
  delete_contents_on_destroy = var.allow_nonempty_delete
}

output "dataset_name" {
  value = google_bigquery_dataset.dataset.dataset_id
}

output "gcp_id" {
  value = google_bigquery_dataset.dataset.id
}

output "gcp_project_id" {
  value = var.gcp_project_id
}
