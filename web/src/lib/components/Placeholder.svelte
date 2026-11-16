<script lang="ts">
	// Stands in for a page's charts and tables until they are built, and shows
	// how many rows of data reached the page (proof the data loading works).
	import { LOCALES, messages, type Language } from '#lib/i18n/index.ts';

	let { lang, rowCount }: { lang: Language; rowCount: number } = $props();

	const m = $derived(messages(lang));
	const count = $derived(new Intl.NumberFormat(LOCALES[lang]).format(rowCount));
</script>

<p class="placeholder">{m.comingSoon} {m.rowsLoaded(count)}</p>

<style>
	.placeholder {
		padding: var(--space-m);
		background: var(--color-surface);
		border: 1px dashed var(--color-border);
		color: var(--color-muted);
	}
</style>
