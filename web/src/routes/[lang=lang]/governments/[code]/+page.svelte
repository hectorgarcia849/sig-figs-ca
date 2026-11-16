<script lang="ts">
	import Placeholder from '#lib/components/Placeholder.svelte';
	import { FEDERAL } from '#lib/governments.ts';
	import { localName, messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const name = $derived.by(() => {
		if (data.code === FEDERAL) return m.federalGovernment;
		const place = data.jurisdictions.find((each) => each.code === data.code);
		return place ? localName(place, data.lang) : data.code;
	});
</script>

<svelte:head>
	<title>{name} | {m.siteName}</title>
</svelte:head>

<h1>{name}</h1>
<Placeholder lang={data.lang} seriesCount={data.series.length + data.municipalTransfers.length} />
