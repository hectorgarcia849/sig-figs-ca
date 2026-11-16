<script lang="ts">
	import Placeholder from '#lib/components/Placeholder.svelte';
	import { localName, messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const name = $derived.by(() => {
		const found = data.functions.find((each) => each.function_id === data.id);
		return found ? localName(found, data.lang) : data.id;
	});
</script>

<svelte:head>
	<title>{name} | {m.siteName}</title>
</svelte:head>

<h1>{name}</h1>
<Placeholder lang={data.lang} rowCount={data.rows.length} />
