provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_pubsub_topic_iam_member" "topic_iam" {
  topic  = google_pubsub_topic.topic.name
  role   = "roles/pubsub.admin"
  member = "serviceAccount:${var.environment_service_account_email}"
}


resource "google_pubsub_topic" "topic" {
  name                       = var.resource_id
  message_retention_duration = var.message_retention_duration
}

output "topic_id" {
  value = google_pubsub_topic.topic.id
}

output "gcp_id" {
  value = google_pubsub_topic.topic.id
}
