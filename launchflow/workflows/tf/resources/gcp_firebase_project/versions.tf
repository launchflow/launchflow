terraform {
  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "5.19.0"
    }
  }
}
