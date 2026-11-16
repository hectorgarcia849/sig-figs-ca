<script lang="ts">
	// Privacy: what the site does (and does not do) with visitors' information.
	import PrivacyEn from '#lib/content/PrivacyEn.svelte';
	import PrivacyFr from '#lib/content/PrivacyFr.svelte';
	import { messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
</script>

<svelte:head>
	<title>{m.privacy} | {m.siteName}</title>
</svelte:head>

<h1>{m.privacy}</h1>

<div class="prose">
	{#if data.lang === 'en'}
		<PrivacyEn />
	{:else}
		<PrivacyFr />
	{/if}
</div>

<style>
	.prose {
		max-width: 48rem;
	}
</style>
