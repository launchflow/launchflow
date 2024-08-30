provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_container_node_pool" "default" {
  name       = var.resource_id
  cluster    = var.cluster_id
  node_count = 1

  node_config {
    preemptible     = var.preemptible
    machine_type    = var.machine_type
    disk_size_gb    = var.disk_size_gb
    disk_type       = var.disk_type
    service_account = var.environment_service_account_email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    labels = {
      nodepool = var.resource_id
    }
    dynamic "guest_accelerator" {
      for_each = var.guest_accelerators != null ? var.guest_accelerators : []
      content {
        type  = guest_accelerator.value.type
        count = guest_accelerator.value.count
      }
    }
  }

  dynamic "autoscaling" {
    for_each = var.autoscaling != null ? [var.autoscaling] : []
    content {
      min_node_count       = autoscaling.value.min_node_count
      max_node_count       = autoscaling.value.max_node_count
      total_min_node_count = autoscaling.value.total_min_node_count
      total_max_node_count = autoscaling.value.total_max_node_count
      location_policy      = autoscaling.value.location_policy
    }
  }
}



output "gcp_id" {
  value = google_container_node_pool.default.id
}
