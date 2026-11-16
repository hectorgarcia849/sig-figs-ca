<script lang="ts">
	// Stands in for a page's charts and tables until they are built, and shows
	// how many data series reached the page (proof the data loading works).
	import { LOCALES, messages, type Language } from '#lib/i18n/index.ts';

	let { lang, seriesCount }: { lang: Language; seriesCount?: number } = $props();

	const m = $derived(messages(lang));
	const count = $derived(
		seriesCount === undefined ? '' : new Intl.NumberFormat(LOCALES[lang]).format(seriesCount)
	);
</script>

<p class="placeholder">
	{m.comingSoon}
	{#if count}{m.seriesLoaded(count)}{/if}
</p>

<style>
	.placeholder {
		padding: var(--space-m);
		background: var(--color-surface);
		border: 1px dashed var(--color-border);
		color: var(--color-muted);
	}
</style>
