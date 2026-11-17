<script lang="ts">
	// One chart block, the same everywhere on the site:
	//
	//     title stating the main point
	//     the chart (passed in)
	//     "View as table" (opens a table of the same figures; works without JavaScript)
	//     notes, the source line with links, and "Download CSV"
	import type { Snippet } from 'svelte';
	import { downloadCsv, type CsvValue } from '#lib/charts/csv.ts';
	import type { TableData } from '#lib/charts/figures.ts';
	import { formatDate } from '#lib/i18n/format.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';
	import type { Source } from '#lib/model/types.ts';
	import DataTable from './DataTable.svelte';

	let {
		title,
		lang,
		table,
		sources,
		csv,
		notes = [],
		children
	}: {
		title: string;
		lang: Language;
		table: TableData;
		sources: Source[]; // the tables the figures come from
		csv: { fileName: string; rows: CsvValue[][] };
		notes?: string[];
		children: Snippet; // the chart
	} = $props();

	const m = $derived(messages(lang));
	const headingId = $props.id();
</script>

<figure aria-labelledby={headingId}>
	<h2 id={headingId}>{title}</h2>

	{@render children()}

	<details>
		<summary>{m.viewAsTable}</summary>
		<DataTable {table} caption={title} {lang} />
	</details>

	<figcaption>
		{#each notes as note (note)}
			<p>{note}</p>
		{/each}
		{#each sources as source (source.source_id)}
			<p>
				{m.sourcePrefix}
				{m.tableWord}
				<!-- A link to Statistics Canada, not a page of this site. -->
				<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
				<a href={lang === 'en' ? source.url_en : source.url_fr}>{source.table_number}</a>,
				{m.releasedOn(formatDate(source.release, lang))}
			</p>
		{/each}
		<button type="button" onclick={() => downloadCsv(csv.fileName, csv.rows)}>
			{m.downloadCsv}
		</button>
	</figcaption>
</figure>

<style>
	figure {
		margin: 0 0 var(--space-xl);
	}

	h2 {
		font-size: 1.25rem;
	}

	details {
		margin: var(--space-s) 0;
	}

	summary {
		cursor: pointer;
		color: var(--color-accent);
	}

	figcaption {
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	figcaption p {
		margin: var(--space-xs) 0;
	}

	button {
		font: inherit;
		margin-top: var(--space-s);
		padding: var(--space-xs) var(--space-s);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		color: var(--color-text);
		cursor: pointer;
	}
</style>
