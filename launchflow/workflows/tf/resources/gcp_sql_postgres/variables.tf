#
# LaunchFlow global tofu variables
#

variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "resource_id" {
  type = string
}

variable "environment_service_account_email" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

#
# Postgres specific variables
#

variable "postgres_db_version" {
  type = string
}

variable "db_name" {
  type     = string
  nullable = true
  default  = null
}

variable "user_name" {
  type     = string
  nullable = true
  default  = null
}

variable "postgres_db_tier" {
  type = string
}

variable "postgres_db_edition" {
  type = string
}

variable "allow_public_access" {
  type = bool
}

variable "availability_type" {
  type = string
}

variable "deletion_protection" {
  type = bool
}

variable "include_default_db" {
  type = bool
}

variable "include_default_user" {
  type = bool
}

variable "disk_size_gb" {
  type = number
}

variable "database_flags" {
  type    = map(any)
  default = null
}
