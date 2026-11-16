# web: the public site

A SvelteKit site, built ahead of time into plain HTML files (one per address,
in English and French), with the data each page needs built into it. After the
first page loads, it behaves like a single-page app: links and switches update
the page without a full reload.

## How it gets its data

```
uv run pst export     (from the repository root) writes web/data/*.json
pnpm build            reads web/data/ and writes the finished site to web/build/
```

`src/lib/server/data.ts` reads the JSON files. It runs only while the site is
built, so the large files never reach a browser: each page's `+page.server.ts`
picks out the rows that page needs, and `src/lib/server/series.ts` turns them
into series (one line of figures over the years each), which is what the page
receives.

## Charts

Every chart is one `ChartFigure` block: a title stating the main point, the
chart, "View as table", notes, the source line and "Download CSV". The chart,
table, notes and CSV all read the same `Line` or `Bar` list (`src/lib/figures.ts`),
so they always agree.

Charts are drawn with Observable Plot while the site is built, so they are in
the HTML from the start, and redrawn in the browser when a switch changes.
While building there is no browser, so `hooks.server.ts` gives Plot a stand-in
page (linkedom), which never reaches visitors.

## Commands

Run from the repository root with `just`, or from this folder with `pnpm`:

| just               | pnpm (in web/)                         |                                                        |
| ------------------ | -------------------------------------- | ------------------------------------------------------ |
| `just web-setup`   | `pnpm install`                         | install packages                                       |
| `just web-dev`     | `pnpm dev`                             | run locally with live reload, at http://localhost:5173 |
| `just web-build`   | `pnpm build`                           | build the site into `build/`                           |
| `just web-preview` | `pnpm preview`                         | serve `build/` at http://localhost:4173                |
| `just web-check`   | `pnpm check && pnpm lint && pnpm test` | types, formatting and lint, tests                      |
| `just site`        |                                        | export the newest build, then build the site           |

pnpm comes with Node: turn it on once with `corepack enable pnpm`.

## Layout

```
src/
  app.html, app.css        page shell; colours and spacing as CSS variables
  hooks.server.ts          sets <html lang> on each built page
  params.ts                only "en" and "fr" are valid at the start of an address
  lib/
    types.ts               the shape of each file in web/data/, and of series
    governments.ts         the government pages: "federal", then each province and territory
    measures.ts            the five measures (dollars, inflation-adjusted, per person, ...)
    format.ts              numbers, years and dates in Canadian English and French
    figures.ts             lines and bars, key figures, and the tables, notes and CSV made from them
    totals.ts              adding series together (e.g. 10 functions into a total), year-on-year change
    titles.ts              chart titles that state the main point (facts only, never judgments)
    names.ts               names of governments and functions in the page's language
    csv.ts                 writing and downloading CSV files
    choices.svelte.ts      switch settings kept while browsing from page to page
    charts/                trend and ranking charts (Observable Plot)
    i18n/                  interface text (en.ts, fr.ts) and language helpers
    server/data.ts         reads web/data/ at build time
    server/series.ts       turns exported rows into series
    components/            KeyFigures; SpendingOverview (key figures and charts for one government)
    components/charts/     ChartFigure, Chart, DataTable
    content/               long text, one file per language (the methodology)
    components/controls/   the switches: measure, year, and any choice of a few
  routes/
    +page.svelte           /  the bilingual welcome page
    [lang=lang]/           every page in one language: /en/... and /fr/...
      governments/[code]/  one page per government
      functions/[id]/      one page per function of government
      methodology/         methodology and sources
```

Imports from `src/lib` are written `#lib/...` with the file's extension, e.g.
`#lib/i18n/index.ts`: Node loads some of these files directly while building.
