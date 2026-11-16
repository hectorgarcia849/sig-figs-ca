# Which Terraform and Google providers this setup needs, and where Terraform
# keeps its record of what it made (the "state").
#
# The state is kept in a Cloud Storage bucket, made once by "just infra-setup",
# which also tells Terraform the bucket's name.

terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.0"
    }
  }

  backend "gcs" {
    prefix = "public_spend_tracker/infra"
  }
}

# Every call is billed and quota-checked against our own project, not the
# shared project behind "gcloud auth application-default login".
provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

# Turning services on must not be quota-checked against the project, because
# the services that do the checking may not be on yet.
provider "google" {
  alias                 = "without_quota_project"
  project               = var.project_id
  region                = var.region
  user_project_override = false
}
