provider "google" {
  project = var.gcp_project_id
}

# Create a Cloud Run service for the service
resource "google_cloud_run_v2_service" "service" {

  lifecycle {
    ignore_changes = [
      template[0].annotations,
      template[0].labels,
      template[0].timeout,
      template[0].containers[0].image,
      template[0].containers[0].volume_mounts,
      template[0].containers[0].liveness_probe,
      template[0].containers[0].startup_probe,
      template[0].volumes,
      template[0].execution_environment,
      template[0].encryption_key,
      template[0].session_affinity,
      template[0].timeout
    ]
  }

  name         = var.resource_id
  location     = var.region != null ? var.region : var.gcp_region
  launch_stage = "BETA"

  template {
    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count

    }
    max_instance_request_concurrency = var.max_instance_request_concurrency
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }
      dynamic "ports" {
        for_each = var.port != null ? [1] : []
        content {
          container_port = var.port
        }

      }
      env {
        name  = "LAUNCHFLOW_ARTIFACT_BUCKET"
        value = "gs://${var.artifact_bucket}"
      }
      env {
        name  = "LAUNCHFLOW_PROJECT"
        value = var.launchflow_project
      }
      env {
        name  = "LAUNCHFLOW_ENVIRONMENT"
        value = var.launchflow_environment
      }
      env {
        name  = "LAUNCHFLOW_CLOUD_PROVIDER"
        value = "gcp"
      }
      dynamic "env" {
        for_each = var.environment_variables != null ? var.environment_variables : {}
        content {
          name  = env.key
          value = env.value
        }
      }
    }

    service_account = var.environment_service_account_email
    vpc_access {
      network_interfaces {
        network = "projects/${var.gcp_project_id}/global/networks/default"

      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  custom_audiences = var.custom_audiences
  ingress          = var.ingress
}

# NOTE: This is what allows the service to be accessed by the public
resource "google_cloud_run_v2_service_iam_member" "noauth" {
  count    = var.publicly_accessible ? 1 : 0
  project  = google_cloud_run_v2_service.service.project
  location = google_cloud_run_v2_service.service.location
  name     = google_cloud_run_v2_service.service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = toset(var.invokers)
  project  = google_cloud_run_v2_service.service.project
  location = google_cloud_run_v2_service.service.location
  name     = google_cloud_run_v2_service.service.name
  role     = "roles/run.invoker"
  member   = each.value
}


output "service_url" {
  value = google_cloud_run_v2_service.service.uri
}

output "gcp_id" {
  value = google_cloud_run_v2_service.service.id
}
