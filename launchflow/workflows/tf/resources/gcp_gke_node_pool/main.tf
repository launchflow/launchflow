provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_container_node_pool" "default" {
  name       = var.resource_id
  cluster    = var.cluster_id
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "e2-medium"

    service_account = var.environment_service_account_email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    labels = {
      nodepool = var.resource_id
    }
  }
}



output "gcp_id" {
  value = google_container_node_pool.default.id
}
