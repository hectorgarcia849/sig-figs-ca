# public_spend_tracker

A public, non-partisan explorer of Canadian government spending: federal, every
province and every territory, grouped by function of government (COFOG). Every
figure links to its source.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.

**Status:** step 1 (local pipeline) and step 2 (the public site, in English
and French) are complete. The site is ready to publish on Firebase Hosting at a
free web.app address (see [infra/README.md](infra/README.md)); a custom domain
can be added later. Step 3's Compare page is built (from data files made with
the site; the API is deferred until it is needed). Next: step 4, automation.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and, for the site, Node 24 with
pnpm (turn it on once with `corepack enable pnpm`). [just](https://just.systems)
is optional (`brew install just`); each command is also shown in plain form.

```bash
just setup          # or: uv sync --all-packages && pnpm --dir web install
```

## Use

Everything goes through one command, `pst`:

```bash
just update         # or: uv run pst update     download new releases, then build if anything new arrived
just status         # or: uv run pst status     what is downloaded and built
just extract        # or: uv run pst extract    download only
just build          # or: uv run pst build      build only
just approve        # or: uv run pst approve    approve the newest build for the public site
just export         # or: uv run pst export     write the approved build's data to web/data/
just sync-pull      # or: uv run pst sync pull  bring the bucket's new files into data/
just sync-push      # or: uv run pst sync push  send data/'s new files to the bucket
```

Downloads land in `data/raw/source=statcan/table=<number>/release=<date>/`;
only tables with a new release are downloaded. `update` stops before building
if any download fails, and only builds when a download is newer than the
newest build (`build` always builds).

Each build checks every dataset and saves only if every check passes. The
result is `data/serving/build=<id>/fiscal.duckdb`, with `build_manifest.json`
recording how it was made. The database holds the model tables plus the
measure views defined in [schema/serving.sql](schema/serving.sql).

A build is only a candidate until it is approved: `approve` records the
newest complete build (or the one given, e.g. `pst approve <id>` to roll back)
in `data/serving/current.json`. `export` copies the approved build's figures
into JSON files in `web/data/` (not kept in git), which the site is built from.
Export another build with `--build <id>` (e.g. to look at it before approving
it) or to another folder with `--out <folder>`.

The permanent copy of `data/` is the Cloud Storage bucket
`gs://ca-pol-econ-data` (same folders; see `infra/storage.tf`). `pst sync`
copies between them with `gcloud storage rsync`: it never deletes anything,
never overwrites a file already at the other end, and copies manifests last,
so a half-finished sync is ignored like a half-finished download. The approval
(`serving/current.json`) always comes down with a pull, and only goes up with
`pst sync push --with-approval`. Add `--dry-run` to see what would be copied.

To use a data folder other than `./data`, pass `--data-root` (e.g.
`uv run pst --data-root /tmp/test build`) or set `PST_DATA_ROOT`.

Every run of `extract`, `build`, `approve` or `export` writes a log to `data/logs/`. Problems that
need attention start with `SOURCE CHANGED` (Statistics Canada changed a table)
or `CHECK FAILED`:

```bash
grep -rE "SOURCE CHANGED|CHECK FAILED" data/logs/
```

## The site

```bash
just site           # or: uv run pst export && pnpm --dir web build
just web-preview    # or: pnpm --dir web preview      then open http://localhost:4173
just web-dev        # or: pnpm --dir web dev          live reload while editing
```

See [web/README.md](web/README.md) for how the site is put together, and
[infra/README.md](infra/README.md) for publishing it:

```bash
just deploy-preview # build from the approved build, check every page, put it on a preview address
just deploy-live    # make the reviewed preview the live site
```

## Tests and checks

```bash
just test           # or: uv run pytest
just lint           # or: uv run ruff check . && uv run ruff format --check .
just web-check      # or: pnpm --dir web check && pnpm --dir web lint && pnpm --dir web test
just web-e2e        # or: pnpm --dir web build && pnpm --dir web test:e2e
```

`web-e2e` opens every page of the built site in a real browser (Chromium,
installed by `just setup`) and checks it loads without errors, has no serious
accessibility problems (axe), links to the same page in the other language,
and fits a phone screen.

Tests run offline against a fake Statistics Canada server.

## Layout

```
docs/PLAN.md                 the plan
schema/serving.sql           the measure views: the contract with the API and site
pipeline/                    the data pipeline (Python package)
  src/public_spend_tracker_pipeline/
    cli.py                   the pst command: extract, build, update, status, approve, export
    common/settings.py       tables and governments we use, folders, connection settings
    common/paths.py          where every data file lives
    common/logs.py           logging to the screen and a log file per run
    common/sync.py           pst sync: copies between data/ and the Cloud Storage bucket
    common/http_client.py    web connections that retry brief server problems
    extract/statcan.py       downloads Statistics Canada tables as published
    transform/base.py        what every transformer declares, and shared checks
    transform/staged_statcan.py  cleans each Statistics Canada table into a staged dataset
    transform/statcan_sql.py     SQL pieces shared by the model transformers
    transform/model_reference.py jurisdictions and the COFOG function tree
    transform/model_spending.py  spending in the four views, and municipal transfers
    transform/model_context.py   CPI, population and GDP by fiscal and calendar year
    transform/model_sources.py   the source behind every figure, with links
    build/run.py             runs every step in order, checks, saves the database
    build/serving.py         adds the measure views and build_info, and checks them
    build/needed.py          whether the downloads are newer than the newest build
    release/approve.py       records which build the public site shows
    release/export.py        writes a build's figures as JSON for the site
  tests/
web/                         the public site (SvelteKit); see web/README.md
infra/                       Terraform for Firebase Hosting, and deploy.sh; see infra/README.md
justfile                     every project command
```

## Licences

- **Code:** MIT (see [LICENSE](LICENSE)).
- **Figures published by the site** (including CSV downloads):
  [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/),
  crediting this site and Statistics Canada.
- **Statistics Canada data** is used under the
  [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
