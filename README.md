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
    extract/statcan.py       downloads Statistics Canada tables as published
  tests/
justfile                     every project command
```

## Data licence

Statistics Canada data is used under the
[Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
