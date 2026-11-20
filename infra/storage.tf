# The data bucket: the permanent copy of the pipeline's data folder, with the
# same folders as data/ (raw, staged, model, serving, logs). "pst sync" copies
# between the two; the scheduled pipeline (GitHub Actions) works from it.
#
#   private       public access is blocked outright
#   kept forever  nothing is deleted automatically: the whole folder is a few
#                 tens of megabytes, and raw downloads are the revision history
#   versioning    a replaced file's old version is kept for a year. Only the
#                 approval (serving/current.json) is ever replaced, so this
#                 keeps a history of approvals.

locals {
  data_bucket_name = "${var.project_id}-data"

  # How long a replaced file's old version is kept.
  replaced_versions_kept_days = 365
}

resource "google_storage_bucket" "data" {
  name     = local.data_bucket_name
  location = upper(var.region)

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = local.replaced_versions_kept_days
    }
    action {
      type = "Delete"
    }
  }

  # Terraform refuses to delete the bucket while it holds data.
  force_destroy = false

  depends_on = [google_project_service.services]
}
