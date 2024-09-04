provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_project_service" "notebooks" {
  project = var.gcp_project_id
  service = "notebooks.googleapis.com"

  disable_dependent_services = true
  disable_on_destroy         = false
}

# Wait for the service to be enabled
# No alternatives atm: https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/guides/google_project_service#newly-activated-service-errors
resource "time_sleep" "wait_30_seconds" {
  depends_on = [google_project_service.notebooks]

  create_duration = "30s"
}

resource "google_workbench_instance" "instance" {
  depends_on = [time_sleep.wait_30_seconds]

  name     = var.resource_id
  location = var.zone

  gce_setup {
    container_image {
      repository = "us-docker.pkg.dev/deeplearning-platform-release/gcr.io/base-cu113.py310"
      tag        = "latest"
    }
    service_accounts {
      email = var.environment_service_account_email
    }
  }
}

resource "google_workbench_instance_iam_member" "member" {
  project  = google_workbench_instance.instance.project
  location = google_workbench_instance.instance.location
  name     = google_workbench_instance.instance.name
  role     = "roles/admin"
  member   = "serviceAccount:${var.environment_service_account_email}"
}

output "instance_id" {
  value = google_workbench_instance.instance.id
}

output "instance_url" {
  value = google_workbench_instance.instance.proxy_uri
}
