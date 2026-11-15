# public_spend_tracker: plan

Status: planning complete for M1, nothing built yet. This project replaces
`govt_policy` (the US/Canada trade-action tracker) entirely and will live in a
new repository, `public_spend_tracker`.

## Goal

A public, non-partisan explorer of Canadian government spending, federal and
every province and territory. It shows what the money goes to, who proposed
and approved it, who benefits, and how it compares across provinces, with
other countries and with the wider economy. Every figure links to its source.

| Tier | Audience | What they get |
|---|---|---|
| Free | Public | Level 1 (where the money goes) and level 2 (who benefits), party origin, context |
| Paid (later) | Businesses, researchers | Level 3 (estimated economic effects) and level 4 (program evaluation), exports, API, alerts |

Everything is free for now. The free tier builds the credibility the paid tier
depends on.

## Decisions

| Area | Decision |
|---|---|
| Jurisdictions | Federal, all 10 provinces, all 3 territories |
| What counts as spending | Everything in the budget, including tax expenditures |
| Excluded | Crown corporations, Canada and Quebec Pension Plans |
| Municipalities | Not tracked on their own; included in the province-wide view, shown as a transfer bucket in the provincial-government view |
| Main grouping | COFOG (UN/OECD Classification of the Functions of Government): 10 functions |
| Second tag | COFOG sub-functions, only where they pass accuracy checks |
| Secondary tags | Economic type, who benefits, region, our own themes |
| History | As far back as clean data allows; no PDF digging |
| Revisions | Every figure is stored with the Statistics Canada release it came from |
| Languages | Bilingual data; basic free machine translation for French interface text |
| Accessibility | WCAG 2.1 AA |

## Spending views

The Statistics Canada data supports four views. Every page states which one it shows.

| View | Source | Detail | Use |
|---|---|---|---|
| **Federal** | 10-10-0024-01 | 10 functions + sub-functions | Federal pages |
| **Province-wide** | 10-10-0005-01 | 10 functions + sub-functions | Default for each province and for every comparison between provinces (function pages, map, Compare) |
| **Provincial government only** | 10-10-0024-01, plus 10-10-0020-01 for the municipal bucket | 10 functions only | What the provincial government itself spends; where party and budget-measure data will attach later |
| **Canada combined** | 10-10-0005-01 | 10 functions + sub-functions | National totals |

Why two province views: each province splits services differently between the
province and its municipalities. Ontario, for example, spent $6.7B on policing
provincially and $8.7B through municipalities in 2024-25. Comparing provincial
governments alone would mislead, and Statistics Canada advises against it.
Province-wide figures combine the province with its municipalities, hospitals,
school boards, universities and colleges, and remove transfers among them, so
provinces can be compared fairly.

Canada combined removes transfers between governments (about $140B in 2024-25),
so each dollar is counted once. For example, housing support: federal $5.1B
plus province-wide $10.8B, but Canada combined is $10.8B, because the federal
amount was transferred to provinces and cities that spent it.

## Data findings (checked 2026-11-12)

- **Years:** fiscal 2008-09 to 2024-25. Statistics Canada's year "2024" means
  fiscal 2024-25 (April to March). The 2025-26 release is expected around late
  November 2026.
- **Revisions:** the latest year is marked preliminary and the year before revised.
- **Accuracy:** sub-functions add up to their function totals within $2–3M
  (rounding). Statistics Canada publishes about 50 sub-functions; some minor
  groups are merged into "not elsewhere classified".
- **Gaps:** the provincial-government-only view has no sub-functions. Municipal
  sub-functions exist only from 2016.
- **Operating spending only:** the function figures exclude capital purchases
  (roads, buildings, equipment) and depreciation. This matters most for
  transport and housing, and the methodology page must say so prominently.
- **Interest:** interest on all government debt is under General public services.
- **Exclusions already applied by Statistics Canada:** Crown corporations
  (government business enterprises) and the pension plans are excluded from
  every view we use. No adjustment needed.
- **Tax expenditures:** not in this data. They arrive in M2 from the federal
  Report on Federal Tax Expenditures, then from provincial reports.
- **Municipal bucket:** municipalities' "grants from general government units".
  It includes some federal money and is not broken down by function.
- **Reconciliation:** federal function total ($519.7B in 2024-25) equals federal
  expense ($534.5B) minus depreciation ($14.8B). Provincial totals reconcile the
  same way.

## Context data

| Series | Source | Frequency | Fiscal-year conversion |
|---|---|---|---|
| Consumer price index | 18-10-0004-01 (territories use capital cities) | Monthly | Exact: April–March average |
| Population | 17-10-0009-01 | Quarterly | Exact: July 1 estimate |
| National GDP | 36-10-0104-01 | Quarterly | Exact: sum of four quarters |
| Provincial GDP | 36-10-0222-01 | Annual | Blended: 75% of year N + 25% of year N+1 |

Each context value is stored twice: the fiscal-year value (with a column
recording the method: exact or blended) and the plain calendar-year value.

Measures shown on the site: nominal dollars, real dollars (latest fiscal year's
dollars by default, adjusted with each jurisdiction's own CPI), per person, real
per person, and share of GDP. They are defined once in `schema/serving.sql`.

## Milestones

| | Milestone | Level |
|---|---|---|
| M1 | **Backbone:** the four views above, by COFOG function and sub-function, with context data. **Ship a public view right after M1.** | 1 |
| M2 | **Federal detail:** spending by department and program, estimates vs. actuals, tax expenditures | 1 |
| M3 | **Federal measures:** budget measures linked from announced → authorized → spent; PBO costings; party origin and votes | 1 |
| M4 | **Provincial detail:** M2–M3 for each province, ordered by data quality and population | 1 |
| M5 | **Who benefits:** recipients, regions and ridings, industries, budget impacts reports, income distribution | 2 |
| M6 | **Explorer:** government → party → function → measure → recipient → source | 1–2 |
| M7 | **Global context:** OECD and IMF comparisons, economic backdrop | context |
| M8+ | **Paid tier:** economic multipliers, simulations with ranges, program evaluations, API and exports | 3–4 |

## M1 technical design

### Pipeline (Python)

```
Statistics Canada data API (free, no key)
  → raw      files exactly as downloaded, with manifest; never edited, kept forever
  → staged   cleaned and typed, one dataset per source table
  → model    jurisdictions, COFOG functions, spending, context, sources
  → serving  one DuckDB file the API serves
```

- **Extractors** fetch source files into `raw/` and write a manifest
  (URL, fetch time, checksum, release date).
- **Transformers** (plain Python classes) each produce one dataset. Each declares
  its name, inputs, a `transform()` (DuckDB SQL or Python) and `checks()`
  (for example: sub-functions add up to their function, no duplicate keys,
  labels present in both languages).
- **A small runner** runs transformers in dependency order, writes Parquet,
  records lineage, and stops the build if a check fails.

### Storage (Cloud Storage, one bucket)

```
gs://public_spend_tracker-data-prod/
├── raw/source=statcan/table=<product_id>/release=<date>/   (files + _manifest.json)
├── staged/dataset=<name>/release=<date>/data.parquet
├── model/dataset=<name>/build=<build_id>/data.parquet
└── serving/
    ├── build=<build_id>/fiscal.duckdb + build_manifest.json
    └── current.json      record of the approved build
```

Every folder below the top level is named "label=value", so tools such as
DuckDB can read the release date or build ID straight from the path. A build ID
is the UTC time the build started, e.g. `20261114-153000`.

Raw files are kept forever (they hold the revision history). Staged and model
outputs can be regenerated and expire after a set period.

### Serving

- The approved DuckDB file is **built into the API's container image** at
  release. Each data release is a new Cloud Run version, so code and data are
  always tested and deployed together, and rollback is Cloud Run's built-in
  version rollback.
- Revisit when recipient-level data (M5) makes the file large: mount the bucket
  read-only, or move large tables to BigQuery or Postgres.
- Measures (real, per person, share of GDP) are defined once as SQL views
  inside the DuckDB build.

### API (FastAPI on Cloud Run, read-only)

```
GET /api/v1/meta            build id, releases, years, measures, notes
GET /api/v1/governments     codes, type, English and French labels
GET /api/v1/functions       COFOG tree with sub-function availability
GET /api/v1/spending        ?gov= &function= &level=1|2 &from= &to=
                            &measure=nominal|real|per_capita|real_per_capita|pct_gdp
                            &counting=federal|province_wide|provincial_government|canada
                            &context=fiscal|calendar &format=json|csv
GET /api/v1/context         ?gov= &series=population,cpi,gdp
GET /api/v1/sources/{id}    source table, release, link, checksum
```

Data responses use codes only; labels come from the reference endpoints.
Every response carries units, build id and source ids. Long cache lifetimes,
keyed to the build id. TypeScript types are generated from the API's OpenAPI
spec so the front end cannot drift from it.

### Front end (SvelteKit + TypeScript)

- Pages are pre-built at release with their own data included (about 200
  pages: ~100 addresses × 2 languages). After loading, controls update charts
  instantly in the browser. Only the Compare page calls the API.
- Pages: Home (Canada combined), Government (×14), Function (×10 and
  sub-functions), Compare, Methodology and sources, About.
- Province pages switch between **Province-wide** (default) and
  **Provincial government only**.
- Shared controls: measure, year, view, language; calendar-year context values
  behind an advanced toggle.
- Addresses shared across languages: `/en/governments/on`, `/fr/governments/on`.
- Every chart: takeaway title, "view as table", source line, CSV download, units
  shown, colour-blind-safe palette.
- Libraries: Paraglide (translation), Observable Plot and d3-hierarchy (charts),
  simplified Statistics Canada boundaries (map), plain CSS with Svelte scoped
  styles and CSS variables.
- Number formatting follows Canadian English and French conventions
  ("$12.3B" / "12,3 G$").

### Release process

1. The pipeline runs on a schedule (GitHub Actions), builds, runs checks and
   writes a **"what changed" report**: new years, revised past figures, check results.
2. The release **waits for approval** (GitHub environment protection).
3. On approval: build the API image with the approved DuckDB file, deploy to
   Cloud Run, rebuild the pages from the same data, deploy to Firebase Hosting.
4. After release: automatic checks that live numbers match the build, and a
   **release summary** for review. The same summary feeds the public revision
   history on the Methodology page.

### Hosting and cost (Google Cloud, `us-central1`)

| Need | Service |
|---|---|
| Data files | Cloud Storage |
| API | Cloud Run, scale to zero, capped maximum instances |
| Front end and CDN | Firebase Hosting, with `/api` routed to Cloud Run |
| Pipeline and deploys | GitHub Actions, using workload identity federation (no stored keys) |
| Images | Artifact Registry |
| Infrastructure | Terraform |
| Guardrail | Billing budget alert |

Environments: local and prod only. Expected cost for M1: roughly $0–5 a month
plus a domain, within the free tiers (to confirm against current pricing).

## Repository layout

```
public_spend_tracker/
├── README.md
├── justfile                  one command list: setup, test, pipeline, dev, release
├── pyproject.toml            uv workspace root
├── docs/                     PLAN.md, methodology.md, decisions/
├── schema/serving.sql        contract between pipeline and API
├── pipeline/                 extract → transform → build (Python)
├── api/                      FastAPI + Dockerfile (Python)
├── web/                      SvelteKit + TypeScript
├── infra/                    Terraform
└── .github/workflows/        ci.yml, pipeline.yml, release.yml
```

Tooling: `uv`, `ruff`, `pyright`, `pytest` for Python; `pnpm`, `svelte-check`,
ESLint, Prettier, Vitest, Playwright (with axe accessibility checks) for the web.

## Deferred topics

- Visitor analytics and privacy (Quebec's privacy law requires consent for
  tracking; cookieless analytics avoids a banner)
- Monitoring: uptime checks, error reporting
- Visual identity: typography, colours, chart style guide
- Security basics: dependency updates, least-privilege service accounts
- Governing-party band on trend charts
- Licensing of code and derived data

## Principles

- Every figure links to its source table and release.
- The method is published and applied the same way to every government and party.
- Limitations are stated where the figures appear, not only on the methodology page.
- Not legal or investment advice.

## Licensing of sources

Statistics Canada data is used under the Open Government Licence – Canada,
which allows commercial use with attribution.
