provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}


data "google_compute_network" "default_private_network" {
  name = "default"
}



locals {
  database_flags = var.database_flags == null ? [] : [
    for flag, value in var.database_flags : {
      key   = flag
      value = value
    }
  ]
}

resource "google_sql_database_instance" "cloud_sql_instance" {
  name             = var.resource_id
  project          = var.gcp_project_id
  database_version = var.postgres_db_version
  region           = var.gcp_region
  settings {
    tier      = var.postgres_db_tier
    edition   = var.postgres_db_edition
    disk_size = var.disk_size_gb
    dynamic "database_flags" {
      for_each = local.database_flags[*]
      content {
        name  = database_flags.value.key
        value = database_flags.value.value
      }
    }
    ip_configuration {
      // Use a dynamic block for conditionally adding authorized_networks
      dynamic "authorized_networks" {
        for_each = var.allow_public_access ? [1] : []
        content {
          name  = "default"
          value = "0.0.0.0/0" # Allows all IP addresses to connect
        }
      }
      # TODO: investigate removing require_ssl, it was removed in future versions of the provider
      require_ssl     = var.allow_public_access ? false : true
      ssl_mode        = var.allow_public_access ? "ENCRYPTED_ONLY" : "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"
      ipv4_enabled    = var.allow_public_access
      private_network = data.google_compute_network.default_private_network.id
    }
    availability_type = var.availability_type
    backup_configuration {
      start_time                     = "03:00"
      enabled                        = true
      point_in_time_recovery_enabled = true
      location                       = "us"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
      }
    }
    # NOTE: This adds protection to the instance to prevent accidental deletion
    deletion_protection_enabled = var.deletion_protection
  }
  # NOTE: This only protects at the terraform level, not the GCP level
  deletion_protection = var.deletion_protection
}

resource "google_sql_user" "cloud_sql_user" {
  count      = var.include_default_user ? 1 : 0
  depends_on = [google_sql_database_instance.cloud_sql_instance]

  name     = var.user_name
  instance = google_sql_database_instance.cloud_sql_instance.name
  password = random_password.user-password[0].result
  project  = var.gcp_project_id
  # NOTE: We use the ABANDON deletion policy since Postgres databases not owned by the
  # cloudsqlsuperuser cannot be deleted by the API
  deletion_policy = "ABANDON"
}

resource "google_sql_database" "cloud_sql_database" {
  count = var.include_default_db ? 1 : 0
  depends_on = [
    google_sql_database_instance.cloud_sql_instance,
    google_sql_user.cloud_sql_user
  ]

  lifecycle {
    # There are issues updating deletion policy after and import so just ignore it.
    ignore_changes = [deletion_policy]
  }

  name     = var.db_name
  instance = google_sql_database_instance.cloud_sql_instance.name
  project  = var.gcp_project_id
  # NOTE: We use the ABANDON deletion policy since Postgres databases not owned by the
  # cloudsqlsuperuser cannot be deleted by the API
  deletion_policy = "ABANDON"
}


resource "random_password" "user-password" {
  count   = var.include_default_user ? 1 : 0
  length  = 16
  special = true
}


locals {
  database_name = var.include_default_db ? google_sql_database.cloud_sql_database[0].name : ""
  user          = var.include_default_user ? google_sql_user.cloud_sql_user[0].name : ""
  password      = var.include_default_user ? random_password.user-password[0].result : ""
}

output "database_name" {
  description = "The instance name for the master instance"
  value       = local.database_name
}

output "connection_name" {
  description = "The connection name of the master instance to be used in connection strings"
  value       = google_sql_database_instance.cloud_sql_instance.connection_name
}

output "user" {
  description = "The user name for the database."
  value       = local.user
}

output "password" {
  description = "The auto-generated default user password if no input password was provided"
  value       = local.password
  sensitive   = true
}

output "gcp_id" {
  value = google_sql_database_instance.cloud_sql_instance.id
}

output "public_ip_address" {
  description = "The public IP address of the master instance"
  value       = google_sql_database_instance.cloud_sql_instance.public_ip_address
}

output "private_ip_address" {
  description = "The private IP address of the master instance"
  value       = google_sql_database_instance.cloud_sql_instance.private_ip_address
}

output "public_ip_enabled" {
  value = google_sql_database_instance.cloud_sql_instance.settings[0].ip_configuration[0].ipv4_enabled
}
