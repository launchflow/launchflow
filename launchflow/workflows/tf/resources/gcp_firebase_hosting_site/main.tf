provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


resource "google_firebase_hosting_site" "default" {
  provider = google-beta
  project  = var.gcp_project_id
  site_id  = var.resource_id
}


resource "google_firebase_hosting_custom_domain" "default" {
  count    = var.custom_domain != null ? 1 : 0
  provider = google-beta

  project               = var.gcp_project_id
  site_id               = google_firebase_hosting_site.default.site_id
  custom_domain         = var.custom_domain
  wait_dns_verification = false
}

output "default_url" {
  value = google_firebase_hosting_site.default.default_url
}

output "desired_dns_records" {
  description = "The set of DNS records Hosting needs to serve secure content on the domain."
  value = flatten([
    for domain in google_firebase_hosting_custom_domain.default :
    [
      for update in domain.required_dns_updates :
      [
        for desired_record in update.desired :
        [
          for record in desired_record.records :
          "${record.type},${record.rdata}"
        ]
      ]
    ]
  ])
}


output "gcp_id" {
  value = google_firebase_hosting_site.default.id
}
