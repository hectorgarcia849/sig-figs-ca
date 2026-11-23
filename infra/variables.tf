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

variable "github_repository" {
  description = "The GitHub repository whose Actions jobs may sign in, as \"owner/name\"."
  type        = string

  validation {
    condition     = can(regex("^[^/]+/[^/]+$", var.github_repository))
    error_message = "Write the repository as \"owner/name\"."
  }
}

variable "github_repository_id" {
  description = <<-EOT
    The repository's permanent number, which GitHub never reuses, e.g.
    "123456789" (see https://api.github.com/repos/<owner>/<name>, "id").
    Sign-in is limited by this number rather than the name.
  EOT
  type        = string
}

variable "github_owner_id" {
  description = <<-EOT
    The repository owner's permanent number, e.g. "12345678" (see
    https://api.github.com/users/<owner>, "id"). GitHub puts it in the name
    of every job that signs in.
  EOT
  type        = string
}
