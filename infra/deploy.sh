#!/usr/bin/env bash
# Put the site on Firebase Hosting, in two steps, so every release is looked at
# before the public sees it:
#
#   infra/deploy.sh preview   export the approved build, build the site, run the
#                             page checks, and put it on a temporary preview
#                             address (shown at the end) for you to review
#   infra/deploy.sh live      make that exact preview the live site, then check
#                             the live site shows the approved build
#
# Run from anywhere; normally through "just deploy-preview" and "just deploy-live".
# Needs "just infra-apply" to have run once (the site's name and address come
# from Terraform).
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREVIEW_CHANNEL="preview"
PREVIEW_LIFETIME="7d"
# The Firebase "deploy target" name used in web/firebase.json.
TARGET="site"

cd "$REPOSITORY_ROOT"

output() { terraform -chdir=infra output -raw "$1"; }
PROJECT="$(output project_id)"
SITE="$(output site_id)"
SITE_URL="$(output site_url)"

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

case "${1:-}" in
preview)
	uv run pst export
	SITE_URL="$SITE_URL" pnpm --dir web build
	pnpm --dir web test:e2e
	point_target_at_site
	(cd web && firebase hosting:channel:deploy "$PREVIEW_CHANNEL" \
		--only "$TARGET" --expires "$PREVIEW_LIFETIME" --project "$PROJECT")
	echo
	echo "Review the preview address above. When it looks right: just deploy-live"
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
