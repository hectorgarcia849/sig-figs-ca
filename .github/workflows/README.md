# GitHub Actions: checks, new data and releases

Two workflows run on GitHub. Neither stores a key or password: the jobs that
need Google Cloud sign in with a short-lived token that Google only accepts
from this repository (see `infra/github.tf`).

## `ci.yml`: Checks

The same tests and code checks as `just test`, `just lint` and
`just web-check`, for every pull request and every push to `main`. It has no
access to Google Cloud, so it is safe for changes proposed by anyone.

## `pipeline.yml`: Data and releases

Runs on weekdays at 15:00 UTC, on every push to `main` (except changes to
docs alone), and from the **Run workflow** button.

1. **Preview** (the pipeline robot: can read the data bucket and add files to
   it, never replace or delete them):
   - brings down the bucket, then `pst update` downloads new Statistics Canada
     releases and builds if anything new arrived;
   - decides what to release:

     | What happened | Released |
     | --- | --- |
     | new data | the new build: `pst diff` writes the "what changed" report and the CSV of every revision, and the build is saved to the bucket |
     | code pushed to `main`, no new data | the site's new code, with the approved build |
     | scheduled run, nothing new | nothing: the run stops here |

   - builds the site, checks every page in a real browser, puts it on the
     preview address (kept 30 days) and opens an issue titled
     **"Review release: ..."** with the preview link, the report and a link to
     approve.
2. **Release** (the release robot: as above, and may also replace the
   approval file, `serving/current.json`) waits for you:
   - **Approve** on the run's page ("Review deployments"): it records the
     approval in the bucket (new data only), makes the exact preview you
     reviewed the live site, checks the live `/build.json` names the approved
     build, and closes the issue.
   - **Reject**: nothing changes. The build stays in the bucket, not
     approved; close the issue yourself.

Only one run happens at a time. A run waiting for approval holds its place
(for up to 30 days), and newer runs queue behind it.

GitHub emails you when a run is waiting for your approval and when a
scheduled run fails (for example, when Statistics Canada changes a table's
columns: the log says SOURCE CHANGED). In a public repository, GitHub pauses
scheduled runs after 60 days with no commits; it emails first, and one click
turns them back on.

## Settings the workflows need

**Repository variables** (Settings > Secrets and variables > Actions >
Variables). None is a secret: they name things, and grant nothing. Terraform
lists them all:

```bash
terraform -chdir=infra output github_variables
```

| Variable | What |
| --- | --- |
| `GCP_PROJECT` | the Google Cloud project |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | where jobs sign in to Google Cloud |
| `GCP_PIPELINE_SERVICE_ACCOUNT` | the preview job's robot |
| `GCP_RELEASE_SERVICE_ACCOUNT` | the release job's robot |
| `FIREBASE_SITE` | the Firebase Hosting site's name |
| `SITE_URL` | the site's public address |
| `PST_DATA_BUCKET` | the data bucket |

**The `production` environment** (Settings > Environments), with you as the
required reviewer and only the `main` branch allowed to deploy. The release
robot only trusts jobs in this environment.

**Actions settings** (Settings > Actions > General):

- Workflow permissions: read only. Each job asks for exactly what it needs.
- Approval for running workflows from forks: required for all outside
  contributors.
- Actions permissions: only the actions below, and only when pinned to a full
  commit. The allowed list: `actions/checkout`, `actions/setup-node`,
  `astral-sh/setup-uv`, `pnpm/action-setup`, `google-github-actions/auth` and
  `google-github-actions/setup-gcloud`, each written as `owner/name@*`. A new
  action has to be added there before a workflow can use it.

## Versions

Every action is pinned to an exact commit, with its version in a comment, so
a new release of an action cannot change what runs with the robots' access.
To update one, look up the new release's commit and change both. GitHub
refuses to run an action that is not pinned this way.
