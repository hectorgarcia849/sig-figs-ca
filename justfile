# Every command for this project. Run `just` to list them.
# Install just with: brew install just

# List the available commands
default:
    @just --list

# Install Python, the site's packages and every dependency
setup:
    uv sync --all-packages
    pnpm --dir web install
    pnpm --dir web exec playwright install chromium

# Run all tests
test:
    uv run pytest

# Check code style and formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Download new Statistics Canada releases into data/raw/
extract:
    uv run pst extract

# Build the database from everything downloaded, checking every step
build:
    uv run pst build

# Download, then build if anything new arrived: the everyday command
update:
    uv run pst update

# Bring the bucket's new files (and its approval) down into data/
sync-pull *options:
    uv run pst sync pull {{options}}

# Send data/'s new files up to the bucket (add --with-approval to send the approval too)
sync-push *options:
    uv run pst sync push {{options}}

# Show downloads, builds and the approved build (changes nothing)
status:
    uv run pst status

# Approve a build for the public site: the newest complete one, or the one given
approve *build:
    uv run pst approve {{build}}

# Write the approved build's figures as JSON for the site (web/data/)
export:
    uv run pst export

# Install the site's packages (needs pnpm: corepack enable pnpm)
web-setup:
    pnpm --dir web install

# Run the site locally with live reload, at http://localhost:5173
web-dev:
    pnpm --dir web dev

# Build the site into web/build/ from web/data/ (run "just export" first)
web-build:
    pnpm --dir web build

# Serve the built site at http://localhost:4173
web-preview:
    pnpm --dir web preview

# Check the site: types, formatting and lint, tests
web-check:
    pnpm --dir web check
    pnpm --dir web lint
    pnpm --dir web test

# Build the site, then check every page in a real browser (errors, accessibility, layout)
web-e2e: web-build
    pnpm --dir web test:e2e

# Export the approved build, then build the site
site: export web-build

# --- Google Cloud and Firebase Hosting (see infra/README.md) ---

# One-time: switch on the basic services, then make the bucket for Terraform's records
infra-setup project:
    gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project={{project}}
    gcloud auth application-default set-quota-project {{project}}
    gcloud storage buckets create gs://{{project}}-tfstate --project={{project}} --location=us-central1 --uniform-bucket-level-access --public-access-prevention
    gcloud storage buckets update gs://{{project}}-tfstate --versioning
    terraform -chdir=infra init -backend-config=bucket={{project}}-tfstate

# Show what Terraform would change in Google Cloud (changes nothing)
infra-plan:
    terraform -chdir=infra plan

# Make Terraform's changes in Google Cloud (asks before changing anything)
infra-apply:
    terraform -chdir=infra apply

# Build and check the site from the approved build, and put it on a preview address
deploy-preview:
    infra/deploy.sh preview

# Make the reviewed preview the live site
deploy-live:
    infra/deploy.sh live
