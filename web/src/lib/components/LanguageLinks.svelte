<script lang="ts">
	// Links in the page's <head> for search engines: the page's official full
	// address, and the same page in each language (hreflang), so English
	// searchers are sent to /en/... and French searchers to /fr/...
	// The welcome page (/) is the "x-default": where to send everyone else.
	import { LANGUAGES, LOCALES, type Language } from '#lib/i18n/index.ts';

	const WELCOME_PAGE = '/';

	let {
		siteUrl,
		address,
		addresses,
		includeWelcomePage = false
	}: {
		siteUrl: string; // e.g. https://public-spend-tracker.web.app
		address: string; // this page, e.g. /en/governments/on
		addresses: Record<Language, string>; // this page in each language
		includeWelcomePage?: boolean; // only for the welcome page and the language home pages
	} = $props();
</script>

<svelte:head>
	<link rel="canonical" href={siteUrl + address} />
	{#each LANGUAGES as lang (lang)}
		<link rel="alternate" hreflang={LOCALES[lang]} href={siteUrl + addresses[lang]} />
	{/each}
	{#if includeWelcomePage}
		<link rel="alternate" hreflang="x-default" href={siteUrl + WELCOME_PAGE} />
	{/if}
</svelte:head>
