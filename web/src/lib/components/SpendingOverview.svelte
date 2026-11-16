<script lang="ts">
	// One government's spending, as shown on Home and every government page:
	//
	//     key figures for the chosen year (plus any the page adds)
	//     anything the page wants after them (e.g. "who spends it")
	//     chart: total over time
	//     chart: the 10 functions, largest first, linking to their pages
	//     chart: the sub-functions of one function, picked from a list
	//
	// The page passes in the series for the view it shows (e.g. province-wide
	// Ontario, or federal excluding transfers) and the switch settings.
	import type { Snippet } from 'svelte';
	import { resolve } from '$app/paths';
	import { rankingChart } from '#lib/charts/ranking.ts';
	import { trendChart } from '#lib/charts/trend.ts';
	import Chart from '#lib/components/charts/Chart.svelte';
	import ChartFigure from '#lib/components/charts/ChartFigure.svelte';
	import KeyFigures from '#lib/components/KeyFigures.svelte';
	import {
		barsAt,
		figuresCsv,
		headlineFigures,
		measureNotes,
		rankingTable,
		sourcesOf,
		trendTable,
		type KeyFigure,
		type Line
	} from '#lib/figures.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';
	import type { Measure } from '#lib/measures.ts';
	import { functionName } from '#lib/names.ts';
	import { largestPartTitle, largestTitle, overTimeTitle } from '#lib/titles.ts';
	import { sumSeries } from '#lib/totals.ts';
	import type { GovernmentFunction, Source, SpendingSeries } from '#lib/types.ts';

	let {
		lang,
		name,
		fileName,
		series,
		functions,
		years,
		sources,
		baseYear,
		measure,
		yearIndex,
		notes = [],
		extraFigures = [],
		subFunctionsUnavailable,
		afterFigures
	}: {
		lang: Language;
		name: string; // the government, e.g. "Ontario"
		fileName: string; // start of CSV file names, e.g. "ontario-province-wide"
		series: SpendingSeries[]; // functions and sub-functions in the view shown
		functions: GovernmentFunction[];
		years: number[];
		sources: Source[];
		baseYear: number;
		measure: Measure;
		yearIndex: number;
		notes?: string[]; // added to every chart, e.g. what the view counts
		extraFigures?: KeyFigure[];
		subFunctionsUnavailable?: string; // why there are no sub-functions, if there are none
		afterFigures?: Snippet;
	} = $props();

	const m = $derived(messages(lang));
	const year = $derived(years[yearIndex]);
	const allYears = $derived(years.map((_, index) => index));

	/** One line per function or sub-function, named, in the functions list's order. */
	function linesFor(ids: string[]): Line[] {
		return ids.flatMap((id) => {
			const found = series.find((each) => each.function_id === id);
			return found ? [{ label: functionName(functions, id, lang), series: found, id }] : [];
		});
	}

	const functionLines = $derived(
		linesFor(functions.filter((each) => each.level === 1).map((each) => each.function_id))
	);
	const total = $derived(sumSeries(functionLines.map((line) => line.series)));
	const totalLine = $derived({ label: name, series: total });
	const usedSources = $derived(sourcesOf(series, sources));
	const figures = $derived([
		...headlineFigures(total, years, yearIndex, measure, lang),
		...extraFigures
	]);

	const functionBars = $derived(barsAt(functionLines, yearIndex, measure));

	// The function whose sub-functions are shown (health to begin with).
	let chosenFunction = $state('707');
	const subFunctionLines = $derived(
		linesFor(
			functions.filter((each) => each.parent_id === chosenFunction).map((each) => each.function_id)
		)
	);
	const subFunctionBars = $derived(barsAt(subFunctionLines, yearIndex, measure));
	const chosenFunctionName = $derived(functionName(functions, chosenFunction, lang));
</script>

<KeyFigures {figures} />

{@render afterFigures?.()}

<ChartFigure
	title={overTimeTitle(total, years, yearIndex, measure, lang)}
	{lang}
	table={trendTable([totalLine], years, measure, lang)}
	sources={usedSources}
	notes={[
		...measureNotes([totalLine], years, allYears, measure, baseYear, lang),
		...notes,
		m.operatingOnly
	]}
	csv={{
		fileName: `${fileName}-total-${measure}.csv`,
		rows: figuresCsv([totalLine], years, m.government, measure, lang, sources)
	}}
>
	<Chart
		chart={(width) => trendChart([totalLine], years, measure, lang, width)}
		description={overTimeTitle(total, years, yearIndex, measure, lang)}
	/>
</ChartFigure>

<ChartFigure
	title={largestTitle(functionBars, year, lang)}
	{lang}
	table={rankingTable(functionBars, m.function, measure, lang, (bar) =>
		bar.id ? resolve('/[lang=lang]/functions/[id]', { lang, id: bar.id }) : undefined
	)}
	sources={usedSources}
	notes={[...measureNotes(functionLines, years, [yearIndex], measure, baseYear, lang), ...notes]}
	csv={{
		fileName: `${fileName}-functions-${measure}.csv`,
		rows: figuresCsv(functionLines, years, m.function, measure, lang, sources)
	}}
>
	<Chart
		chart={(width) => rankingChart(functionBars, measure, lang, width)}
		description={largestTitle(functionBars, year, lang)}
	/>
</ChartFigure>

<section class="sub-functions" aria-label={m.subFunctions}>
	{#if subFunctionsUnavailable}
		<p class="note">{m.subFunctions}: {subFunctionsUnavailable}</p>
	{:else}
		<label>
			{m.subFunctionsOf}
			<select bind:value={chosenFunction}>
				{#each functionLines as line (line.id)}
					<option value={line.id}>{line.label}</option>
				{/each}
			</select>
		</label>
		<ChartFigure
			title={largestPartTitle(chosenFunctionName, subFunctionBars, year, lang)}
			{lang}
			table={rankingTable(subFunctionBars, m.subFunctions, measure, lang)}
			sources={usedSources}
			notes={[
				...measureNotes(subFunctionLines, years, [yearIndex], measure, baseYear, lang),
				...notes
			]}
			csv={{
				fileName: `${fileName}-${chosenFunction}-sub-functions-${measure}.csv`,
				rows: figuresCsv(subFunctionLines, years, m.subFunctions, measure, lang, sources)
			}}
		>
			<Chart
				chart={(width) => rankingChart(subFunctionBars, measure, lang, width)}
				description={largestPartTitle(chosenFunctionName, subFunctionBars, year, lang)}
			/>
		</ChartFigure>
	{/if}
</section>

<style>
	.sub-functions label {
		display: flex;
		gap: var(--space-s);
		align-items: center;
		margin-bottom: var(--space-m);
		font-weight: 600;
	}

	select {
		font: inherit;
		padding: var(--space-xs) var(--space-s);
	}

	.note {
		color: var(--color-muted);
	}
</style>
