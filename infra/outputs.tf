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
