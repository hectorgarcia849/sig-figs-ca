<script lang="ts">
	// The row of switches at the top of a page (measure, year, view, ...).
	// Choices made here apply to every chart on the page.
	import type { Snippet } from 'svelte';

	let { children, note }: { children: Snippet; note?: string } = $props();
</script>

<div class="switches">
	{@render children()}
	{#if note}
		<p class="note">{note}</p>
	{/if}
</div>

<style>
	.switches {
		margin: var(--space-m) 0;
		padding: var(--space-s) var(--space-m);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
	}

	.note {
		margin: var(--space-xs) 0;
		color: var(--color-muted);
		font-size: 0.875rem;
	}
</style>
