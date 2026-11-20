#!/usr/bin/env bash
# Put the site on Firebase Hosting, in two steps, so every release is looked at
# before the public sees it:
#
#   infra/deploy.sh preview [BUILD_ID]
#                         export a build (the approved one unless given),
#                         build the site, run the page checks, and put it on
#                         a temporary preview address (shown at the end) for
#                         you to review
#   infra/deploy.sh live  make that exact preview the live site, then check
#                         the live site shows the approved build
#
# Run from anywhere: on a laptop through "just deploy-preview" and
# "just deploy-live", and on GitHub by .github/workflows/pipeline.yml.
#
# The project, site and address come from these settings when they are set
# (as on GitHub, whose robot accounts cannot read Terraform's records), and
# otherwise from Terraform (after "just infra-apply" has run once):
#
#   GCP_PROJECT    the Google Cloud project
#   FIREBASE_SITE  the Firebase Hosting site's name
#   SITE_URL       the site's public address
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREVIEW_CHANNEL="preview"
# How long a preview stays up: the longest Firebase allows, so a release
# waiting for approval keeps its preview.
PREVIEW_LIFETIME="30d"
# The Firebase "deploy target" name used in web/firebase.json.
TARGET="site"

cd "$REPOSITORY_ROOT"

output() { terraform -chdir=infra output -raw "$1"; }
PROJECT="${GCP_PROJECT:-$(output project_id)}"
SITE="${FIREBASE_SITE:-$(output site_id)}"
SITE_URL="${SITE_URL:-$(output site_url)}"

# Point the deploy target in web/firebase.json at this project's site
# (written to web/.firebaserc, which is not kept in git). Clearing first means
# a changed site name replaces the old one; the first time there is nothing to clear.
point_target_at_site() {
	(cd web &&
		{ firebase target:clear hosting "$TARGET" --project "$PROJECT" >/dev/null 2>&1 || true; } &&
		firebase target:apply hosting "$TARGET" "$SITE" --project "$PROJECT" >/dev/null)
}

# The build recorded by "pst approve".
approved_build() {
	python3 -c 'import json; print(json.load(open("data/serving/current.json"))["build_id"])'
}

# The preview address, from the Firebase tool's JSON answer on standard input.
preview_address() {
	python3 -c 'import json, sys; print(next(iter(json.load(sys.stdin)["result"].values()))["url"])'
}

case "${1:-}" in
preview)
	build="${2:-}"
	uv run pst export ${build:+--build "$build"}
	SITE_URL="$SITE_URL" pnpm --dir web build
	pnpm --dir web test:e2e
	point_target_at_site
	address="$(cd web && firebase hosting:channel:deploy "$PREVIEW_CHANNEL" \
		--only "$TARGET" --expires "$PREVIEW_LIFETIME" --project "$PROJECT" --json |
		preview_address)"
	# On GitHub, hand the address to the workflow's next steps.
	if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
		echo "preview_url=$address" >>"$GITHUB_OUTPUT"
	fi
	echo
	echo "Preview: $address"
	echo "Review it. When it looks right: just deploy-live"
	;;
live)
	(cd web && firebase hosting:clone "$SITE:$PREVIEW_CHANNEL" "$SITE:live" --project "$PROJECT")
	expected="$(approved_build)"
	published="$(curl -fsS "$SITE_URL/build.json" |
		python3 -c 'import json, sys; print(json.load(sys.stdin)["build_id"])')"
	if [[ "$published" != "$expected" ]]; then
		echo "WARNING: $SITE_URL shows build $published, but the approved build is $expected." >&2
		echo "Run just deploy-preview again, review it, then just deploy-live." >&2
		exit 1
	fi
	echo "Live at $SITE_URL, showing approved build $published."
	;;
*)
	echo "Usage: infra/deploy.sh preview|live" >&2
	exit 2
	;;
esac
