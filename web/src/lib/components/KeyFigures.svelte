<script lang="ts">
	// A row of headline figures for the chosen year, e.g. total spending, per
	// person and share of GDP.
	import type { KeyFigure } from '#lib/figures.ts';

	let { figures }: { figures: KeyFigure[] } = $props();
</script>

<dl class="figures">
	{#each figures as figure (figure.label)}
		<div class="figure">
			<dt>
				{#if figure.href}
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={figure.href}>{figure.label}</a>
				{:else}
					{figure.label}
				{/if}
			</dt>
			<dd class="value">
				{figure.value}{#if figure.mark}<sup>{figure.mark}</sup>{/if}
			</dd>
			{#if figure.detail}
				<dd class="detail">{figure.detail}</dd>
			{/if}
		</div>
	{/each}
</dl>

<style>
	.figures {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
		gap: var(--space-m);
		margin: var(--space-m) 0 var(--space-l);
	}

	.figure {
		padding: var(--space-m);
		background: var(--color-surface);
		border-radius: var(--radius);
	}

	dt {
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	dd {
		margin: 0;
	}

	.value {
		font-size: 1.75rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.detail {
		color: var(--color-muted);
		font-size: 0.875rem;
	}
</style>
