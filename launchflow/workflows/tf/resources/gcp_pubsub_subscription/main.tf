provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_pubsub_subscription_iam_member" "subscription_iam" {
  subscription = google_pubsub_subscription.subscription.name
  role         = "roles/pubsub.admin"
  member       = "serviceAccount:${var.environment_service_account_email}"
}


resource "google_pubsub_subscription" "subscription" {
  name  = var.resource_id
  topic = var.topic

  ack_deadline_seconds       = var.ack_deadline_seconds
  retain_acked_messages      = var.retain_acked_messages
  message_retention_duration = var.message_retention_duration
  filter                     = var.filter

  dynamic "push_config" {
    for_each = var.push_config == null ? [] : [1]
    content {
      attributes    = var.push_config.attributes
      push_endpoint = var.push_config.push_endpoint
      dynamic "oidc_token" {
        for_each = var.push_config.oidc_token == null ? [] : [1]
        content {
          service_account_email = var.push_config.oidc_token.service_account_email
          audience              = var.push_config.oidc_token.audience
        }
      }
    }
  }
}

output "subscription_id" {
  value = google_pubsub_subscription.subscription.id
}

output "gcp_id" {
  value = google_pubsub_subscription.subscription.id
}
