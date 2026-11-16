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
picks out the rows that page needs.

## Commands

Run from the repository root with `just`, or from this folder with `pnpm`:

| just | pnpm (in web/) | |
|---|---|---|
| `just web-setup` | `pnpm install` | install packages |
| `just web-dev` | `pnpm dev` | run locally with live reload, at http://localhost:5173 |
| `just web-build` | `pnpm build` | build the site into `build/` |
| `just web-preview` | `pnpm preview` | serve `build/` at http://localhost:4173 |
| `just web-check` | `pnpm check && pnpm lint && pnpm test` | types, formatting and lint, tests |
| `just site` | | export the newest build, then build the site |

pnpm comes with Node: turn it on once with `corepack enable pnpm`.

## Layout

```
src/
  app.html, app.css        page shell; colours and spacing as CSS variables
  hooks.server.ts          sets <html lang> on each built page
  params.ts                only "en" and "fr" are valid at the start of an address
  lib/
    types.ts               the shape of each file in web/data/
    governments.ts         the government pages: "federal", then each province and territory
    i18n/                  interface text (en.ts, fr.ts) and language helpers
    server/data.ts         reads web/data/ at build time
    components/            shared pieces of pages
  routes/
    +page.svelte           /  the bilingual welcome page
    [lang=lang]/           every page in one language: /en/... and /fr/...
      governments/[code]/  one page per government
      functions/[id]/      one page per function of government
      methodology/         methodology and sources
```

Imports from `src/lib` are written `#lib/...` with the file's extension, e.g.
`#lib/i18n/index.ts`: Node loads some of these files directly while building.
