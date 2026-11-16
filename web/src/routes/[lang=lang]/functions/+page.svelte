<script lang="ts">
	// The list of the 10 functions of government.
	import { resolve } from '$app/paths';
	import { localName, messages } from '#lib/i18n/index.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const functions = $derived(data.functions.filter((each) => each.level === 1));
</script>

<svelte:head>
	<title>{m.functionsTitle} | {m.siteName}</title>
</svelte:head>

<h1>{m.functionsTitle}</h1>
<ul>
	{#each functions as each (each.function_id)}
		<li>
			<a href={resolve('/[lang=lang]/functions/[id]', { lang: data.lang, id: each.function_id })}
				>{localName(each, data.lang)}</a
			>
		</li>
	{/each}
</ul>
