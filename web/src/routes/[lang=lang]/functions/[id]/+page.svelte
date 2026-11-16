<script lang="ts">
	// One function of government across governments:
	//
	//     key figures: all governments combined
	//     chart: each province and territory, ranked (per person by default)
	//     chart: who delivers it over time (federal own spending + provinces = all)
	//     chart: its sub-functions, all governments combined
	import { resolve } from '$app/paths';
	import { choices } from '#lib/choices.svelte.ts';
	import { rankingChart } from '#lib/charts/ranking.ts';
	import { trendChart } from '#lib/charts/trend.ts';
	import Chart from '#lib/components/charts/Chart.svelte';
	import ChartFigure from '#lib/components/charts/ChartFigure.svelte';
	import KeyFigures from '#lib/components/KeyFigures.svelte';
	import MeasureChoice from '#lib/components/controls/MeasureChoice.svelte';
	import Switches from '#lib/components/controls/Switches.svelte';
	import YearSelect from '#lib/components/controls/YearSelect.svelte';
	import {
		barsAt,
		figuresCsv,
		headlineFigures,
		measureNotes,
		rankingTable,
		sourcesOf,
		trendTable,
		type Line
	} from '#lib/figures.ts';
	import { CANADA } from '#lib/governments.ts';
	import { messages } from '#lib/i18n/index.ts';
	import { functionName, nameInView } from '#lib/names.ts';
	import { highestPlaceTitle, largestPartTitle, provincesShareTitle } from '#lib/titles.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const name = $derived(functionName(data.functions, data.id, data.lang));
	// Per person by default here: the fair way to compare provinces of different sizes.
	const measure = $derived(choices.measure ?? 'amount_per_person');
	const year = $derived(choices.year ?? data.years.at(-1)!);
	const yearIndex = $derived(data.years.indexOf(year));
	const allYears = $derived(data.years.map((_, index) => index));
	const baseYear = $derived(data.build.baseYear);

	// Provinces ranked, with all of them combined drawn as the reference bar.
	const provinceLines = $derived(
		data.provinces.map((series) => ({
			label: nameInView(data.jurisdictions, 'province_wide', series.jurisdiction, data.lang),
			series,
			id: series.jurisdiction,
			highlight: series.jurisdiction === CANADA
		}))
	);
	const provinceBars = $derived(barsAt(provinceLines, yearIndex, measure));
	const provincesWithoutCombined = $derived(provinceBars.filter((bar) => bar.id !== CANADA));

	// Who delivers it: federal own spending + all provinces = all governments.
	const allGovernments = $derived(
		data.allGovernments.find((series) => series.function_id === data.id)!
	);
	const allProvinces = $derived(data.provinces.find((series) => series.jurisdiction === CANADA)!);
	const deliveryLines: Line[] = $derived([
		{ label: m.allGovernments, series: allGovernments },
		{ label: m.allProvinces, series: allProvinces },
		...data.federalOwn.map((series) => ({ label: m.federalOwnSpending, series }))
	]);

	// Sub-functions, all governments combined.
	const subFunctionLines = $derived(
		data.allGovernments
			.filter((series) => series.function_id !== data.id)
			.map((series) => ({
				label: functionName(data.functions, series.function_id, data.lang),
				series
			}))
	);
	const subFunctionBars = $derived(barsAt(subFunctionLines, yearIndex, measure));

	const provincesTitle = $derived(
		highestPlaceTitle(name, provincesWithoutCombined, measure, year, data.lang)
	);
	const deliveryTitle = $derived(
		provincesShareTitle(name, allProvinces, allGovernments, yearIndex, year, data.lang)
	);
	const partsTitle = $derived(largestPartTitle(name, subFunctionBars, year, data.lang));
</script>

<svelte:head>
	<title>{name} | {m.siteName}</title>
</svelte:head>

<h1>{name}</h1>
<p class="intro">{m.functionIntro}</p>

<Switches note={m.viewNotes.province_wide}>
	<MeasureChoice lang={data.lang} value={measure} onchange={(value) => (choices.measure = value)} />
	<YearSelect
		lang={data.lang}
		years={data.years}
		value={year}
		onchange={(value) => (choices.year = value)}
	/>
</Switches>

<h2 class="figures-heading">{m.allGovernments}</h2>
<KeyFigures figures={headlineFigures(allGovernments, data.years, yearIndex, measure, data.lang)} />

<ChartFigure
	title={provincesTitle}
	lang={data.lang}
	table={rankingTable(provinceBars, m.government, measure, data.lang, (bar) =>
		bar.id && bar.id !== CANADA
			? resolve('/[lang=lang]/governments/[code]', { lang: data.lang, code: bar.id })
			: undefined
	)}
	sources={sourcesOf(data.provinces, data.sources)}
	notes={[
		...measureNotes(provinceLines, data.years, [yearIndex], measure, baseYear, data.lang),
		m.viewNotes.province_wide
	]}
	csv={{
		fileName: `${data.id}-provinces-${measure}.csv`,
		rows: figuresCsv(provinceLines, data.years, m.government, measure, data.lang, data.sources)
	}}
>
	<Chart
		chart={(width) => rankingChart(provinceBars, measure, data.lang, width)}
		description={provincesTitle}
	/>
</ChartFigure>

<ChartFigure
	title={deliveryTitle}
	lang={data.lang}
	table={trendTable(deliveryLines, data.years, measure, data.lang)}
	sources={sourcesOf(
		deliveryLines.map((line) => line.series),
		data.sources
	)}
	notes={[
		...measureNotes(deliveryLines, data.years, allYears, measure, baseYear, data.lang),
		m.functionTrendNote
	]}
	csv={{
		fileName: `${data.id}-who-spends-${measure}.csv`,
		rows: figuresCsv(deliveryLines, data.years, m.government, measure, data.lang, data.sources)
	}}
>
	<Chart
		chart={(width) => trendChart(deliveryLines, data.years, measure, data.lang, width)}
		description={deliveryTitle}
	/>
</ChartFigure>

{#if subFunctionLines.length > 0}
	<ChartFigure
		title={partsTitle}
		lang={data.lang}
		table={rankingTable(subFunctionBars, m.subFunctions, measure, data.lang)}
		sources={sourcesOf(data.allGovernments, data.sources)}
		notes={measureNotes(subFunctionLines, data.years, [yearIndex], measure, baseYear, data.lang)}
		csv={{
			fileName: `${data.id}-sub-functions-${measure}.csv`,
			rows: figuresCsv(
				subFunctionLines,
				data.years,
				m.subFunctions,
				measure,
				data.lang,
				data.sources
			)
		}}
	>
		<Chart
			chart={(width) => rankingChart(subFunctionBars, measure, data.lang, width)}
			description={partsTitle}
		/>
	</ChartFigure>
{/if}

<style>
	.intro {
		font-size: 1.125rem;
		max-width: 48rem;
	}

	.figures-heading {
		font-size: 1rem;
		margin-bottom: 0;
	}
</style>
