provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_compute_region_autoscaler" "default" {
  name   = var.resource_id
  target = var.instance_group_manager_id
  region = var.region

  dynamic "autoscaling_policy" {
    for_each = var.autoscaling_policies
    content {

      min_replicas    = autoscaling_policy.value.min_replicas
      max_replicas    = autoscaling_policy.value.max_replicas
      cooldown_period = autoscaling_policy.value.cooldown_period

      dynamic "cpu_utilization" {
        for_each = autoscaling_policy.value.cpu_utilization != null ? [autoscaling_policy.value.cpu_utilization] : []
        content {
          target            = cpu_utilization.value.target
          predictive_method = cpu_utilization.value.predictive_method
        }
      }

      dynamic "metric" {
        for_each = autoscaling_policy.value.custom_metric != null ? [autoscaling_policy.value.custom_metric] : []
        content {
          name   = custom_metric.value.name
          target = custom_metric.value.target
          type   = custom_metric.value.type
        }
      }

      dynamic "load_balancing_utilization" {
        for_each = autoscaling_policy.value.load_balancing_utilization != null ? [autoscaling_policy.value.load_balancing_utilization] : []
        content {
          target = load_balancing_utilization.value.target
        }
      }
    }
  }
}

output "gcp_id" {
  value = google_compute_region_autoscaler.default.id
}
