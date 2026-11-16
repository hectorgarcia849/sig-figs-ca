# public_spend_tracker

A public, non-partisan explorer of Canadian government spending: federal, every
province and every territory, grouped by function of government (COFOG). Every
figure links to its source.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.

**Status:** step 1 (local pipeline) is complete: downloading, every
transformer, the database build, the measure views (real dollars, per person,
share of GDP) and the `pst` command all work. Step 2 (the public site) has
started: `pst export` writes the site's data, and the site skeleton in `web/`
builds every page in English and French (placeholder content for now).

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
just update         # or: uv run pst update     download new releases, then build
just status         # or: uv run pst status     what is downloaded and built
just extract        # or: uv run pst extract    download only
just build          # or: uv run pst build      build only
just export         # or: uv run pst export     write the site's data to web/data/
```

Downloads land in `data/raw/source=statcan/table=<number>/release=<date>/`;
only tables with a new release are downloaded. `update` stops before building
if any download fails.

Each build checks every dataset and saves only if every check passes. The
result is `data/serving/build=<id>/fiscal.duckdb`, with `build_manifest.json`
recording how it was made. The database holds the model tables plus the
measure views defined in [schema/serving.sql](schema/serving.sql).

`export` copies the newest complete build's figures into JSON files in
`web/data/` (not kept in git), which the site is built from. Pick a build with
`--build <id>` or another folder with `--out <folder>`.

To use a data folder other than `./data`, pass `--data-root` (e.g.
`uv run pst --data-root /tmp/test build`) or set `PST_DATA_ROOT`.

Every run of `extract`, `build` or `export` writes a log to `data/logs/`. Problems that
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

See [web/README.md](web/README.md) for how the site is put together.

## Tests and checks

```bash
just test           # or: uv run pytest
just lint           # or: uv run ruff check . && uv run ruff format --check .
just web-check      # or: pnpm --dir web check && pnpm --dir web lint && pnpm --dir web test
```

Tests run offline against a fake Statistics Canada server.

## Layout

```
docs/PLAN.md                 the plan
schema/serving.sql           the measure views: the contract with the API and site
pipeline/                    the data pipeline (Python package)
  src/public_spend_tracker_pipeline/
    settings.py              tables and governments we use, folders, connection settings
    cli.py                   the pst command: extract, build, update, status, export
    build.py                 runs every step in order, checks, saves the database
    export.py                writes a build's figures as JSON for the site
    logs.py                  logging to the screen and a log file per run
    serving.py               adds the measure views and build_info, and checks them
    http_client.py           web connections that retry brief server problems
    paths.py                 where every data file lives
    extract/statcan.py       downloads Statistics Canada tables as published
    transform/base.py        what every transformer declares, and shared checks
    transform/staged_statcan.py  cleans each Statistics Canada table into a staged dataset
    transform/statcan_sql.py     SQL pieces shared by the model transformers
    transform/model_reference.py jurisdictions and the COFOG function tree
    transform/model_spending.py  spending in the four views, and municipal transfers
    transform/model_context.py   CPI, population and GDP by fiscal and calendar year
    transform/model_sources.py   the source behind every figure, with links
  tests/
web/                         the public site (SvelteKit); see web/README.md
justfile                     every project command
```

## Data licence

Statistics Canada data is used under the
[Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
