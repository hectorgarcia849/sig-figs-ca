<script lang="ts">
	// The list of government pages: federal, then each province and territory.
	import { resolve } from '$app/paths';
	import { FEDERAL, provincesAndTerritories } from '#lib/governments.ts';
	import { localName, messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const governments = $derived([
		{ code: FEDERAL, name: m.federalGovernment },
		...provincesAndTerritories(data.jurisdictions).map((place) => ({
			code: place.code,
			name: localName(place, data.lang)
		}))
	]);
</script>

<svelte:head>
	<title>{m.governmentsTitle} | {m.siteName}</title>
</svelte:head>

<h1>{m.governmentsTitle}</h1>
<ul>
	{#each governments as government (government.code)}
		<li>
			<a
				href={resolve('/[lang=lang]/governments/[code]', {
					lang: data.lang,
					code: government.code
				})}>{government.name}</a
			>
		</li>
	{/each}
</ul>
