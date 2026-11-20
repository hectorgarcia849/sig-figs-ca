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
  description = "The DNS records to add at your registrar for the custom domain (empty without one)."
  value       = var.custom_domain == null ? [] : google_firebase_hosting_custom_domain.domain[0].required_dns_updates
}

output "data_bucket" {
  description = "The data bucket, as pst sync expects it (PST_DATA_BUCKET)."
  value       = "gs://${google_storage_bucket.data.name}"
}

# For GitHub's repository settings (variables, not secrets: they grant nothing).

output "github_workload_identity_provider" {
  description = "GitHub variable GCP_WORKLOAD_IDENTITY_PROVIDER: where jobs sign in."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_pipeline_service_account" {
  description = "GitHub variable GCP_PIPELINE_SERVICE_ACCOUNT: the daily pipeline's robot."
  value       = google_service_account.pipeline.email
}

output "github_release_service_account" {
  description = "GitHub variable GCP_RELEASE_SERVICE_ACCOUNT: the release's robot."
  value       = google_service_account.release.email
}
