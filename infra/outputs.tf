# What the deploy script and you need to know after "terraform apply".

output "project_id" {
  description = "The Google Cloud project."
  value       = var.project_id
}

output "site_id" {
  description = "The Firebase Hosting site's name."
  value       = google_firebase_hosting_site.site.site_id
}

output "site_url" {
  description = "The site's public address: the custom domain once set, otherwise the free web.app one."
  value       = var.custom_domain == null ? google_firebase_hosting_site.site.default_url : "https://${var.custom_domain}"
}

output "custom_domain_dns_records" {
  description = "The DNS records to add at your registrar for the custom domain and its www redirect (empty without one)."
  value = concat(
    [for domain in google_firebase_hosting_custom_domain.domain : domain.required_dns_updates],
    [for domain in google_firebase_hosting_custom_domain.www : domain.required_dns_updates],
  )
}

output "data_bucket" {
  description = "The data bucket, as pst sync expects it (PST_DATA_BUCKET)."
  value       = "gs://${google_storage_bucket.data.name}"
}

# For GitHub's repository variables (not secrets: none of them grants
# anything). See .github/workflows/README.md.

output "github_variables" {
  description = "Every variable the GitHub workflows read, by name."
  value = {
    GCP_PROJECT                    = var.project_id
    GCP_WORKLOAD_IDENTITY_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_PIPELINE_SERVICE_ACCOUNT   = google_service_account.pipeline.email
    GCP_RELEASE_SERVICE_ACCOUNT    = google_service_account.release.email
    FIREBASE_SITE                  = google_firebase_hosting_site.site.site_id
    SITE_URL                       = var.custom_domain == null ? google_firebase_hosting_site.site.default_url : "https://${var.custom_domain}"
    PST_DATA_BUCKET                = "gs://${google_storage_bucket.data.name}"
  }
}
