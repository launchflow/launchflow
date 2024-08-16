provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_compute_firewall" "default" {
  name                    = var.resource_id
  network                 = "default"
  description             = var.description
  direction               = var.direction
  priority                = var.priority
  destination_ranges      = var.destination_ranges
  source_tags             = var.source_tags
  source_ranges           = var.source_ranges
  target_tags             = var.target_tags
  target_service_accounts = var.target_service_accounts

  dynamic "allow" {
    for_each = var.allow_rules
    content {
      protocol = allow.value.protocol
      ports    = allow.value.ports
    }
  }
}

output "gcp_id" {
  value = google_compute_firewall.default.id
}
