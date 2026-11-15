# public_spend_tracker

A public, non-partisan explorer of Canadian government spending: federal, every
province and every territory, grouped by function of government (COFOG). Every
figure links to its source.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.

**Status:** step 1 (local pipeline) in progress. The Statistics Canada
extractor works; transformers and the database build come next.

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

## Tests and checks

```bash
just test           # or: uv run pytest
just lint           # or: uv run ruff check . && uv run ruff format --check .
```

Tests run offline against a fake Statistics Canada server.

## Layout

```
docs/PLAN.md                 the plan
pipeline/                    the data pipeline (Python package)
  src/public_spend_tracker_pipeline/
    settings.py              tables we use, folders, connection settings
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
