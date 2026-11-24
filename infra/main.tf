# The site's home on Google Cloud: Firebase Hosting, with a billing alert.
#
#   services       the Google Cloud services this setup uses, switched on
#   firebase       Firebase added to the project
#   site           the Firebase Hosting site (free address: <site_id>.web.app)
#   custom domain  only when var.custom_domain is set, with www.<domain>
#                  redirecting to it (unless var.redirect_www is false)
#   budget         an email alert if monthly spending passes var.monthly_budget
#                  (only when var.billing_account is set)
#
# The data bucket is in storage.tf; GitHub Actions' sign-in in github.tf.
#
# The site's files are not uploaded by Terraform: infra/deploy.sh does that
# with the Firebase command line tool, so each release is a reviewable step.

locals {
  services = [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "billingbudgets.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
    "storage.googleapis.com",
    # For GitHub Actions' keyless sign-in (github.tf).
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ]

  # Spending alerts at half, nine tenths and all of the monthly budget.
  budget_alert_shares = [0.5, 0.9, 1.0]
}

data "google_project" "this" {
  project_id = var.project_id
}

resource "google_project_service" "services" {
  provider = google.without_quota_project
  for_each = toset(local.services)

  service = each.value

  # Leave services on if this setup is ever removed: other things may use them.
  disable_on_destroy = false
}

resource "google_firebase_project" "this" {
  provider = google-beta
  project  = var.project_id

  depends_on = [google_project_service.services]
}

resource "google_firebase_hosting_site" "site" {
  provider = google-beta
  project  = google_firebase_project.this.project
  site_id  = var.site_id
}

resource "google_firebase_hosting_custom_domain" "domain" {
  provider = google-beta
  count    = var.custom_domain == null ? 0 : 1

  project       = google_firebase_project.this.project
  site_id       = google_firebase_hosting_site.site.site_id
  custom_domain = var.custom_domain

  # Do not wait for the DNS records: they are added by hand at the registrar,
  # after Terraform lists them.
  wait_dns_verification = false
}

# www.<domain> sends visitors to the domain itself, keeping the rest of the
# address (www.example.ca/en goes to example.ca/en).
resource "google_firebase_hosting_custom_domain" "www" {
  provider = google-beta
  count    = var.custom_domain != null && var.redirect_www ? 1 : 0

  project         = google_firebase_project.this.project
  site_id         = google_firebase_hosting_site.site.site_id
  custom_domain   = "www.${var.custom_domain}"
  redirect_target = var.custom_domain

  wait_dns_verification = false
}

resource "google_billing_budget" "monthly" {
  # Only when a billing account is given. It is set by hand rather than read
  # from the project, because reading it needs the Cloud Billing service,
  # which this setup only switches on.
  count = var.billing_account == null ? 0 : 1

  billing_account = var.billing_account
  display_name    = "public_spend_tracker monthly"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      units = tostring(var.monthly_budget)
    }
  }

  dynamic "threshold_rules" {
    for_each = local.budget_alert_shares
    content {
      threshold_percent = threshold_rules.value
    }
  }

  depends_on = [google_project_service.services]
}
