provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${var.environment_service_account_email}"
}

resource "google_storage_bucket" "bucket" {
  name          = var.resource_id
  project       = var.gcp_project_id
  location      = var.location
  force_destroy = var.force_destroy

  uniform_bucket_level_access = var.uniform_bucket_level_access
}

output "bucket_name" {
  value = google_storage_bucket.bucket.name
}

output "url" {
  value = google_storage_bucket.bucket.url
}

output "gcp_id" {
  value = google_storage_bucket.bucket.id
}
