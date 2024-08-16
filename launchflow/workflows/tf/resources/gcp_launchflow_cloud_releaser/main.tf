provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_service_account" "launchflow_releaser" {
  account_id   = var.resource_id
  display_name = "LaunchFlow Release Service Account"
  description  = "Service account that is used by LaunchFlow to trigger deployments and promotions."
}

resource "google_service_account_iam_member" "launchflow_service_account_user_self" {
  service_account_id = google_service_account.launchflow_releaser.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.launchflow_releaser.email}"
}

resource "google_service_account_iam_member" "launchflow_service_account_user" {
  service_account_id = google_service_account.launchflow_releaser.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.launchflow_service_account}"
}

resource "google_service_account_iam_member" "launchflow_service_account_token_creator" {
  service_account_id = google_service_account.launchflow_releaser.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${var.launchflow_service_account}"
}

# Allows the releaser account to impersonate the environment service account
# This is needed to push deployments to cloud run and other services
resource "google_service_account_iam_member" "launchflow_service_account_env_user" {
  service_account_id = "projects/${var.gcp_project_id}/serviceAccounts/${var.environment_service_account_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.launchflow_releaser.email}"
}

resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = var.artifact_bucket
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.launchflow_releaser.email}"
}

resource "google_project_iam_member" "cloud_run_releaser" {
  count   = length(var.permissions)
  project = var.gcp_project_id
  role    = var.permissions[count.index]
  member  = "serviceAccount:${google_service_account.launchflow_releaser.email}"
}

resource "google_storage_bucket_iam_member" "member" {
  bucket = var.artifact_bucket
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.launchflow_releaser.email}"
}

output "gcp_id" {
  value = google_service_account.launchflow_releaser.id
}

output "service_account_email" {
  value = google_service_account.launchflow_releaser.email
}
