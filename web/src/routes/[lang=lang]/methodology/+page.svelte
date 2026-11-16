<script lang="ts">
	import Placeholder from '#lib/components/Placeholder.svelte';
	import { messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
</script>

<svelte:head>
	<title>{m.methodology} | {m.siteName}</title>
</svelte:head>

<h1>{m.methodology}</h1>
<Placeholder lang={data.lang} />

<h2>{m.sourceTables}</h2>
<ul>
	{#each data.sources as source (source.source_id)}
		<li>
			<!-- External links to Statistics Canada, not pages of this site. -->
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
			<a href={data.lang === 'en' ? source.url_en : source.url_fr}
				>{source.table_number}: {data.lang === 'en' ? source.title_en : source.title_fr}</a
			>
			({m.release}
			{source.release}, {m.doi}
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
			<a href={source.doi}>{source.doi}</a>)
		</li>
	{/each}
</ul>
