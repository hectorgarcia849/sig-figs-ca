<script lang="ts">
	// The figures behind a chart as an accessible table: a heading for each
	// column and row, numbers lined up on the right, and preliminary (p) and
	// revised (r) figures marked.
	import type { TableData } from '#lib/charts/figures.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';

	let {
		table,
		caption,
		lang,
		captionShown = true
	}: {
		table: TableData;
		caption: string;
		lang: Language;
		captionShown?: boolean; // false when a heading just above already says the same
	} = $props();

	const m = $derived(messages(lang));
	const hasMarks = $derived(table.rows.some((row) => row.cells.some((cell) => cell.mark)));
</script>

<div class="scroll">
	<table>
		<caption class:hidden={!captionShown}>{caption}</caption>
		<thead>
			<tr>
				{#each table.columns as column, index (index)}
					<th scope="col">{column}</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each table.rows as row, index (index)}
				<tr>
					<th scope="row">
						{#if row.href}
							<!-- Already resolved by whoever made the table. -->
							<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
							<a href={row.href}>{row.header}</a>
						{:else}
							{row.header}
						{/if}
					</th>
					{#each row.cells as cell, cellIndex (cellIndex)}
						<td
							>{cell.text}{#if cell.mark}<sup>{cell.mark}</sup>{/if}</td
						>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
{#if hasMarks}
	<p class="marks">{m.marksExplained}</p>
{/if}

<style>
	.scroll {
		overflow-x: auto;
	}

	table {
		border-collapse: collapse;
		font-variant-numeric: tabular-nums;
	}

	caption {
		text-align: left;
		font-weight: 600;
		padding-bottom: var(--space-s);
	}

	th,
	td {
		padding: var(--space-xs) var(--space-m) var(--space-xs) 0;
		border-bottom: 1px solid var(--color-border);
	}

	th {
		text-align: left;
		font-weight: 600;
	}

	td {
		text-align: right;
		white-space: nowrap;
	}

	.marks {
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	/* Read by screen readers, not shown. */
	.hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
