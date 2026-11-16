<script lang="ts">
	// Methodology and sources: how the figures are made, then every source table.
	import MethodologyEn from '#lib/content/MethodologyEn.svelte';
	import MethodologyFr from '#lib/content/MethodologyFr.svelte';
	import { formatDate } from '#lib/format.ts';
	import { messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
</script>

<svelte:head>
	<title>{m.methodology} | {m.siteName}</title>
</svelte:head>

<h1>{m.methodology}</h1>

<div class="prose">
	{#if data.lang === 'en'}
		<MethodologyEn />
	{:else}
		<MethodologyFr />
	{/if}

	<section>
		<h2>{m.sourceTables}</h2>
		<ul>
			{#each data.sources as source (source.source_id)}
				<li>
					<!-- External links to Statistics Canada, not pages of this site. -->
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={data.lang === 'en' ? source.url_en : source.url_fr}
						>{source.table_number}: {data.lang === 'en' ? source.title_en : source.title_fr}</a
					>
					({m.releasedOn(formatDate(source.release, data.lang))}, {m.doi}
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={source.doi}>{source.doi}</a>)
				</li>
			{/each}
		</ul>
		<p>
			{m.licenceStatement}
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
			<a href={m.licenceUrl}>{m.licence}</a>.
		</p>
	</section>
</div>

<style>
	.prose {
		max-width: 48rem;
	}

	.prose :global(dt) {
		font-weight: 700;
		margin-top: var(--space-m);
	}

	.prose :global(dd) {
		margin-left: 0;
	}
</style>
