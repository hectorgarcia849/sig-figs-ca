<script lang="ts">
	// The figures behind a chart as an accessible table: a heading for each
	// column and row, numbers lined up on the right, and preliminary (p) and
	// revised (r) figures marked.
	import type { TableData } from '#lib/figures.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';

	let { table, caption, lang }: { table: TableData; caption: string; lang: Language } = $props();

	const m = $derived(messages(lang));
	const hasMarks = $derived(table.rows.some((row) => row.cells.some((cell) => cell.mark)));
</script>

<div class="scroll">
	<table>
		<caption>{caption}</caption>
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
					<th scope="row">{row.header}</th>
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
</style>
