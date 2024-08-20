provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_project_service" "container_service" {
  service = "container.googleapis.com"

  disable_on_destroy = false

}

data "google_compute_network" "default" {
  name = "default"
}

resource "google_compute_subnetwork" "k8_subnetwork" {
  name          = "${var.resource_id}-sub-network"
  network       = data.google_compute_network.default.self_link
  ip_cidr_range = var.subnet_ip_cidr_range

  secondary_ip_range {
    range_name    = "pods-range"
    ip_cidr_range = var.pod_ip_cidr_range
  }

  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = var.service_ip_cidr_range
  }
}

module "gke" {
  depends_on = [google_project_service.container_service]
  source     = "terraform-google-modules/kubernetes-engine/google"
  project_id = var.gcp_project_id
  name       = var.resource_id
  region     = var.region
  regional   = var.regional
  zones      = var.zones
  # TODO: allow these to be configured
  network                  = "default"
  subnetwork               = google_compute_subnetwork.k8_subnetwork.name
  ip_range_pods            = "pods-range"
  ip_range_services        = "services-range"
  remove_default_node_pool = true
  deletion_protection      = var.delete_protection

  # Set a dummy node pool that will never be used / scaled
  # TODO: find a way to remove this there is a limit on the number of pools
  # you can have so this is a temporary workaround. We can probably just fork it
  node_pools = [{
    name               = "dummy-pool"
    initial_node_count = 0
    node_count         = 0
    machine_type       = "n1-standard-1"
    min_count          = 0
    max_count          = 0
    autoscaling        = false
  }]
}


output "gcp_id" {
  value = module.gke.cluster_id
}
