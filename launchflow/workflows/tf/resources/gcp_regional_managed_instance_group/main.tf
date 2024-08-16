provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_compute_region_instance_template" "template" {
  # We make this a tiny vm since it will be replaced when the user deploys
  machine_type = "e2-medium"
  region       = var.region
  project      = var.gcp_project_id
  disk {
    boot         = true
    source_image = "cos-cloud/cos-stable-109-17800-147-54"
  }
  labels = {
    container-vm = "cos-stable-109-17800-147-54"
  }
  scheduling {
    # We make this preemptible so it's cheaper to run
    preemptible       = true
    automatic_restart = false
  }
  metadata = {
    google-logging-enabled    = "true"
    google-monitoring-enabled = "true"
    gce-container-declaration = jsonencode({
      spec = {
        containers    = [{ image = "httpd" }]
        volumes       = []
        restartPolicy = "Always"
      }
    })
  }

  service_account {
    email  = var.environment_service_account_email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  network_interface {
    network = "default"

    access_config {
      // Ephemeral IP
    }
  }
  tags = [var.resource_id]
}

resource "google_compute_region_instance_group_manager" "mig" {
  provider           = google-beta
  base_instance_name = var.base_instance_name
  region             = var.region
  name               = var.resource_id
  target_size        = var.target_size
  version {
    instance_template = google_compute_region_instance_template.template.self_link
  }

  dynamic "auto_healing_policies" {
    for_each = var.auto_healing_policy != null ? [var.auto_healing_policy] : []
    content {
      initial_delay_sec = var.auto_healing_policy.initial_delay_sec
      health_check      = var.auto_healing_policy.health_check
    }
  }

  dynamic "named_port" {
    for_each = var.named_ports != null ? var.named_ports : []
    content {
      name = named_port.value.name
      port = named_port.value.port
    }
  }

  dynamic "update_policy" {
    for_each = var.update_policy != null ? [var.update_policy] : []
    content {
      type                           = var.update_policy.type
      minimal_action                 = var.update_policy.minimal_action
      most_disruptive_allowed_action = var.update_policy.most_disruptive_allowed_action
      instance_redistribution_type   = var.update_policy.instance_redistribution_type
      max_surge_fixed                = var.update_policy.max_surge_fixed
      max_surge_percent              = var.update_policy.max_surge_percentage
      max_unavailable_fixed          = var.update_policy.max_unavailable_fixed
      max_unavailable_percent        = var.update_policy.max_unavailable_percentage
      replacement_method             = var.update_policy.replacement_method
      min_ready_sec                  = var.update_policy.min_ready_sec
    }
  }

  lifecycle {
    # We ignore changes to version since that will change as things are depoyed
    ignore_changes = [version]
  }
}

output "gcp_id" {
  value = google_compute_region_instance_group_manager.mig.id
}
