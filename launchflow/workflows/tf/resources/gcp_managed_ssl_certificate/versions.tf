terraform {
  # NOTE: This is configured at runtime with `tofu init`
  # backend "gcs" {
  # }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.19.0"
    }
  }
}
