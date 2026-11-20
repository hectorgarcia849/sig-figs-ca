# Keyless sign-in for GitHub Actions, and what its jobs may do.
#
# GitHub signs a short-lived token for each job, saying which repository,
# branch, event and environment the job runs for. Google Cloud trusts those
# tokens only from our repository (matched by its permanent number, not its
# name) and swaps them for an hour-long Google token for one of two robot
# accounts (service accounts). No key or password is stored in GitHub.
#
#   pipeline  the daily check. Only jobs on the main branch.
#             Data bucket: read, and add new files. It cannot delete or
#             replace anything, so it cannot change what is approved.
#             Firebase Hosting: deploy (the workflow only deploys previews).
#
#   release   the release, after you approve it on GitHub. Only jobs in the
#             "production" environment, which waits for your approval.
#             Data bucket: as above, plus replacing the approval file,
#             serving/current.json, and nothing else.
#             Firebase Hosting: deploy (promotes the preview to live).
#
# Firebase's roles cannot tell a preview from the live site, so both robots
# can deploy either. The live site is protected by the workflows (the daily
# one only deploys previews), by the main-branch rule above, and by only you
# being able to change main.

locals {
  github_issuer = "https://token.actions.githubusercontent.com"

  # The token's "subject" for each robot's jobs, as GitHub writes it.
  pipeline_subject = "repo:${var.github_repository}:ref:refs/heads/main"
  release_subject  = "repo:${var.github_repository}:environment:production"

  # The address of every token with a given subject, as Google writes it.
  github_principal = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/subject"

  # The approval file, as the release robot's permission condition names it.
  approval_object = "projects/_/buckets/${google_storage_bucket.data.name}/objects/serving/current.json"

  # What both robots may do with the data bucket: read the bucket's settings
  # (gcloud storage rsync needs this to sync the whole bucket), read files,
  # and add new ones. And on Firebase Hosting: deploy.
  bucket_roles = [
    "roles/storage.bucketViewer",
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
  ]
  hosting_role = "roles/firebasehosting.admin"
}

# --- GitHub as a trusted sign-in service -------------------------------------

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Jobs from ${var.github_repository} on GitHub Actions."

  depends_on = [google_project_service.services]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions"

  oidc {
    issuer_uri = local.github_issuer
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Only tokens from our repository, by its number: a new repository made
  # under the same name after a deletion has a different number. Never from
  # "pull_request_target", which runs with the main branch's rights for
  # changes proposed by anyone.
  attribute_condition = <<-EOT
    assertion.repository_id == "${var.github_repository_id}" &&
    assertion.event_name != "pull_request_target"
  EOT
}

# --- The two robots ----------------------------------------------------------

resource "google_service_account" "pipeline" {
  account_id   = "pipeline"
  display_name = "Daily pipeline (GitHub Actions)"
  description  = "Downloads, builds and previews. Can add files to the data bucket, never replace or delete them."

  depends_on = [google_project_service.services]
}

resource "google_service_account" "release" {
  account_id   = "release"
  display_name = "Release (GitHub Actions)"
  description  = "Publishes an approved build. Can also replace the approval file, serving/current.json."

  depends_on = [google_project_service.services]
}

# Which GitHub jobs may act as each robot.
resource "google_service_account_iam_member" "pipeline_from_github" {
  service_account_id = google_service_account.pipeline.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "${local.github_principal}/${local.pipeline_subject}"
}

resource "google_service_account_iam_member" "release_from_github" {
  service_account_id = google_service_account.release.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "${local.github_principal}/${local.release_subject}"
}

# --- What the robots may do --------------------------------------------------

resource "google_storage_bucket_iam_member" "pipeline_bucket" {
  for_each = toset(local.bucket_roles)

  bucket = google_storage_bucket.data.name
  role   = each.value
  member = google_service_account.pipeline.member
}

resource "google_storage_bucket_iam_member" "release_bucket" {
  for_each = toset(local.bucket_roles)

  bucket = google_storage_bucket.data.name
  role   = each.value
  member = google_service_account.release.member
}

# Replacing a file needs the right to delete it; the release robot has that
# for the approval file only.
resource "google_storage_bucket_iam_member" "release_replaces_approval" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectUser"
  member = google_service_account.release.member

  condition {
    title       = "approval-file-only"
    description = "Only serving/current.json, the record of the approved build."
    expression  = "resource.name == \"${local.approval_object}\""
  }
}

resource "google_project_iam_member" "pipeline_hosting" {
  project = var.project_id
  role    = local.hosting_role
  member  = google_service_account.pipeline.member
}

resource "google_project_iam_member" "release_hosting" {
  project = var.project_id
  role    = local.hosting_role
  member  = google_service_account.release.member
}
