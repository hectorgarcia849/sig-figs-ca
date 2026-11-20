# infra: the site's home on Google Cloud

Terraform sets up Firebase Hosting in your Google Cloud project; `deploy.sh`
puts the site on it. Until there is a custom domain, the site is published at
its free address, `https://<site_id>.web.app` (`public-spend-tracker` by default).

## What Terraform makes

| File           | What                                                                  |
| -------------- | --------------------------------------------------------------------- |
| `storage.tf`   | the private data bucket (`<project>-data`): the permanent copy of `data/`, kept forever, with a year of old versions |
| `main.tf`      | services switched on, Firebase added, the Hosting site, an optional custom domain, a monthly budget alert |
| `github.tf`    | keyless sign-in for GitHub Actions, and its two robot accounts: `pipeline` (read the bucket, add files) and `release` (the same, and replace the approval file) |
| `variables.tf` | the settings: project, site name, custom domain, billing account, budget amount, GitHub repository |
| `outputs.tf`   | the site's name and address (read by `deploy.sh`), DNS records for a custom domain, the GitHub variables (`github_variables`) |
| `versions.tf`  | Terraform and provider versions; state kept in a Cloud Storage bucket |

Terraform does not upload the site's files: `deploy.sh` does, so every release
is a step you take on purpose.

## First time

You need `gcloud`, `terraform` and `firebase-tools`, and a Google Cloud project
you own. Sign in once with `gcloud auth application-default login` (and
`firebase login` if the Firebase tool asks).

1. Make the bucket for Terraform's records, and connect Terraform to it:

   ```bash
   just infra-setup <project-id>
   ```

2. Copy `terraform.tfvars.example` to `terraform.tfvars` and fill in
   `project_id`, and `billing_account` for the budget alert (shown by
   `gcloud billing projects describe <project-id>`). Set `site_id` if you
   want a different free address.

3. Look at what will be made, then make it:

   ```bash
   just infra-plan
   just infra-apply
   ```

   If adding Firebase fails with a message about terms of service, open the
   project once in the [Firebase console](https://console.firebase.google.com)
   and accept them, then run `just infra-apply` again.

## Each release

GitHub Actions does this on its own, waiting for your approval before
anything goes live: see [.github/workflows/README.md](../.github/workflows/README.md). By hand,
from a laptop:

```bash
just update            # download new releases and build
just approve           # approve the newest build (or: just approve <build_id>)
just deploy-preview    # build the site from it, check every page, put it on a preview address
                       # (or preview any build: infra/deploy.sh preview <build_id>)
just deploy-live       # make that preview the live site, and check it shows the approved build
```

The preview address lasts 30 days. `deploy-live` publishes exactly what you
reviewed, without building again. To roll back, approve the earlier build and
release it the same way.

## Adding a domain later

1. Buy the domain.
2. Set `custom_domain = "example.ca"` in `terraform.tfvars` and run `just infra-apply`.
3. Add the records from `terraform -chdir=infra output custom_domain_dns_records`
   at your registrar. Firebase sets up HTTPS once it sees them (this can take a
   few hours).
4. Run `just deploy-preview` and `just deploy-live`, so the pages' links to
   themselves (for search engines) use the new address. The web.app address
   keeps working.
