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
table, notes and CSV all read the same `Line` or `Bar` list (`src/lib/charts/figures.ts`),
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
| `just web-e2e`     | `pnpm build && pnpm test:e2e`          | check every built page in a real browser               |
| `just site`        |                                        | export the approved build, then build the site         |

pnpm comes with Node: turn it on once with `corepack enable pnpm`.

## Page checks (e2e/)

`pnpm test:e2e` serves `build/` on port 4174 and opens it in Chromium
(Playwright). It checks every page in the sitemap: no console errors (a script
blocked by the security policy shows up as one), no serious or critical
accessibility problems (axe), a canonical link, and links to the same page in
the other language. It also checks the skip link and switches by keyboard,
phone-width layout, chart descriptions, CSV downloads, the "page not found"
page and `build.json`. Install the browser once with
`pnpm exec playwright install chromium`.

## Publishing

The site is published on Firebase Hosting (see `../infra/README.md`).
`firebase.json` holds the hosting rules: addresses without `.html`, security
headers, and caching (a year for files whose names change with their content,
five minutes for pages and data files, so a release shows up quickly).

The full address the site is published at is given at build time as
`SITE_URL` (the deploy script takes it from Terraform; local builds use
http://localhost:4173). Pages use it for the links search engines read: each
page's canonical address and the same page in the other language (hreflang),
`sitemap.xml` and `robots.txt`.

Every page carries a content security policy (set in `vite.config.ts`): only
the site's own scripts run. `build.json` names the approved build the site
shows, so anyone can check which data is live.

## Layout

The files directly in `web/` are configuration that each tool (and editor
extension) looks for next to `package.json`, so they stay there:

```
package.json, pnpm-*.yaml  packages and scripts; pnpm settings
vite.config.ts             SvelteKit: build, security policy, site address; unit tests (vitest)
tsconfig.json              TypeScript (extends the one SvelteKit generates)
eslint.config.js           lint rules
prettier.config.js         formatting (.prettierignore: files it skips)
firebase.json              hosting rules: headers, caching, clean addresses
e2e/                       page checks, with their own playwright.config.ts

Not kept in git: data/ (from "pst export"), build/ (the site), .svelte-kit/,
.firebase/ and .firebaserc (deploy), e2e/test-results/
```

```
src/
  app.html, app.css        page shell; colours and spacing as CSS variables
  hooks.server.ts          sets <html lang> on each built page
  params.ts                only "en" and "fr" are valid at the start of an address
  lib/
    model/                 what the data means (no page code)
      types.ts             the shape of each file in web/data/, and of series
      measures.ts          the five measures (dollars, inflation-adjusted, per person, ...)
      governments.ts       the government pages: "federal", then each province and territory
      names.ts             names of governments and functions in the page's language
      totals.ts            adding series together (e.g. 10 functions into a total), year-on-year change
    charts/                everything a chart block is made of
      figures.ts           lines and bars, key figures, and the tables, notes and CSV made from them
      titles.ts            chart titles that state the main point (facts only, never judgments)
      csv.ts               writing and downloading CSV files
      draw.ts, trend.ts, ranking.ts   drawing trend and ranking charts (Observable Plot)
    i18n/
      en.ts, fr.ts         interface text
      index.ts             language helpers
      format.ts            numbers, years and dates in Canadian English and French
    server/                runs only at build time
      data.ts              reads web/data/
      series.ts            turns exported rows into series
      pages.ts             every page address, for the sitemap
    components/            KeyFigures; SpendingOverview (key figures and charts for one government);
                           LanguageLinks (canonical and hreflang links for search engines)
      charts/              ChartFigure, Chart, DataTable
      controls/            the switches: measure, year, and any choice of a few
    state/choices.svelte.ts   switch settings kept while browsing from page to page
    content/               long text, one file per language (methodology, privacy)
  routes/
    +page.svelte           /  the bilingual welcome page
    [lang=lang]/           every page in one language: /en/... and /fr/...
      governments/[code]/  one page per government
      functions/[id]/      one page per function of government
      methodology/         methodology, sources and licences
      privacy/             what the site does with visitors' information
    404/                   "page not found" in both languages, built as 404.html
    sitemap.xml/, robots.txt/, build.json/   files built with the site
```

Imports from `src/lib` are written `#lib/...` with the file's extension, e.g.
`#lib/i18n/index.ts`: Node loads some of these files directly while building.
