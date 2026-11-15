# public_spend_tracker

A public, non-partisan explorer of Canadian government spending: federal, every
province and every territory, grouped by function of government (COFOG). Every
figure links to its source.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.

**Status:** step 1 (local pipeline) in progress. Downloading, every
transformer, the database build and the measure views (real dollars, per
person, share of GDP) work.

## Setup

Requires [uv](https://docs.astral.sh/uv/). [just](https://just.systems) is
optional (`brew install just`); each command is also shown in plain form.

```bash
just setup          # or: uv sync --all-packages
```

## Use

Download the latest release of every Statistics Canada table we use:

```bash
just extract        # or: uv run python -m public_spend_tracker_pipeline.extract.statcan
```

Files land in `data/raw/source=statcan/table=<number>/release=<date>/`. Running
it again only downloads tables that have a new release. Set `PST_DATA_ROOT` to
store data somewhere other than `./data`.

Build the database from everything downloaded:

```bash
just build          # or: uv run python -m public_spend_tracker_pipeline.build
```

Each build checks every dataset and saves only if every check passes. The
result is `data/serving/build=<id>/fiscal.duckdb`, with `build_manifest.json`
recording how it was made. The database holds the model tables plus the
measure views defined in [schema/serving.sql](schema/serving.sql).

Every run writes a log to `data/logs/`. Problems that need attention start with
`SOURCE CHANGED` (Statistics Canada changed a table) or `CHECK FAILED`:

```bash
grep -rE "SOURCE CHANGED|CHECK FAILED" data/logs/
```

## Tests and checks

```bash
just test           # or: uv run pytest
just lint           # or: uv run ruff check . && uv run ruff format --check .
```

Tests run offline against a fake Statistics Canada server.

## Layout

```
docs/PLAN.md                 the plan
schema/serving.sql           the measure views: the contract with the API and site
pipeline/                    the data pipeline (Python package)
  src/public_spend_tracker_pipeline/
    settings.py              tables and governments we use, folders, connection settings
    build.py                 runs every step in order, checks, saves the database
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
justfile                     every project command
```

## Data licence

Statistics Canada data is used under the
[Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
