# The settings for this setup. Put your values in terraform.tfvars (see
# terraform.tfvars.example); that file is not kept in git.

variable "project_id" {
  description = "The Google Cloud project the site lives in, e.g. \"my-project-123\"."
  type        = string
}

variable "region" {
  description = "Where Google Cloud resources are made."
  type        = string
  default     = "us-central1"
}

variable "site_id" {
  description = <<-EOT
    The Firebase Hosting site's name, which is also its free address:
    "public-spend-tracker" is published at https://public-spend-tracker.web.app.
    Names are shared by everyone on Firebase, so it must not be taken already.
  EOT
  type        = string
  default     = "public-spend-tracker"
}

variable "custom_domain" {
  description = <<-EOT
    A domain you own to publish the site at, e.g. "example.ca", or null to use
    only the free web.app address. After setting it, add the DNS records that
    "terraform output custom_domain_dns_records" lists at your registrar.
  EOT
  type        = string
  default     = null
}

variable "billing_account" {
  description = <<-EOT
    The billing account the project is linked to, e.g. "012345-6789AB-CDEF01"
    (see "gcloud billing projects describe <project>"), for the budget alert.
    Leave it null to have no budget alert.
  EOT
  type        = string
  default     = null
}

variable "monthly_budget" {
  description = <<-EOT
    A monthly spending amount, in the billing account's currency, that sends an
    email alert to the billing account's administrators at 50%, 90% and 100%.
    It is an alert only: nothing is switched off.
  EOT
  type        = number
  default     = 10
}
