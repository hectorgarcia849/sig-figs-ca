<script lang="ts">
	// Home: what all governments in Canada spend, counting each dollar once.
	import { resolve } from '$app/paths';
	import { choices } from '#lib/choices.svelte.ts';
	import KeyFigures from '#lib/components/KeyFigures.svelte';
	import SpendingOverview from '#lib/components/SpendingOverview.svelte';
	import MeasureChoice from '#lib/components/controls/MeasureChoice.svelte';
	import Switches from '#lib/components/controls/Switches.svelte';
	import YearSelect from '#lib/components/controls/YearSelect.svelte';
	import { figureTile } from '#lib/figures.ts';
	import { FEDERAL } from '#lib/governments.ts';
	import { messages } from '#lib/i18n/index.ts';
	import { sumSeries } from '#lib/totals.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const measure = $derived(choices.measure ?? 'amount');
	const year = $derived(choices.year ?? data.years.at(-1)!);
	const yearIndex = $derived(data.years.indexOf(year));

	// Who spends it: federal own spending + all provinces and territories = all governments.
	const parts = $derived([
		{
			label: m.federalOwnSpending,
			series: sumSeries(data.federalOwn),
			href: resolve('/[lang=lang]/governments/[code]', { lang: data.lang, code: FEDERAL })
		},
		{
			label: m.allProvinces,
			series: sumSeries(data.allProvinces),
			href: resolve('/[lang=lang]/governments', { lang: data.lang })
		}
	]);
	const whoSpends = $derived(
		parts.map((part) => ({
			...figureTile(part.label, part.series, measure, data.years, yearIndex, data.lang),
			href: part.href
		}))
	);
</script>

<svelte:head>
	<title>{m.homeTitle} | {m.siteName}</title>
	<meta name="description" content={m.siteDescription} />
</svelte:head>

<h1>{m.homeTitle}</h1>
<p class="intro">{m.homeIntro}</p>

<Switches>
	<MeasureChoice lang={data.lang} value={measure} onchange={(value) => (choices.measure = value)} />
	<YearSelect
		lang={data.lang}
		years={data.years}
		value={year}
		onchange={(value) => (choices.year = value)}
	/>
</Switches>

<SpendingOverview
	lang={data.lang}
	name={m.allGovernments}
	fileName="canada-all-governments"
	series={data.canada}
	functions={data.functions}
	years={data.years}
	sources={data.sources}
	baseYear={data.build.baseYear}
	{measure}
	{yearIndex}
>
	{#snippet afterFigures()}
		<section aria-labelledby="who-spends">
			<h2 id="who-spends">{m.whoDelivers}</h2>
			<KeyFigures figures={whoSpends} />
			<p class="note">{m.whoDeliversNote}</p>
		</section>
	{/snippet}
</SpendingOverview>

<style>
	.intro {
		font-size: 1.125rem;
		max-width: 48rem;
	}

	.note {
		color: var(--color-muted);
		font-size: 0.875rem;
		max-width: 48rem;
		margin-bottom: var(--space-l);
	}
</style>
