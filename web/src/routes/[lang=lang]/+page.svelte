<script lang="ts">
	import Placeholder from '#lib/components/Placeholder.svelte';
	import { messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
</script>

<svelte:head>
	<title>{m.homeTitle} | {m.siteName}</title>
	<meta name="description" content={m.siteDescription} />
</svelte:head>

<h1>{m.homeTitle}</h1>
<Placeholder lang={data.lang} rowCount={data.rows.length} />
