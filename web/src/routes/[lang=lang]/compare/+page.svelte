<script lang="ts">
	// Compare governments side by side:
	//
	//     choices: governments (up to 7), spending on, measure, switches, year
	//     chart: one line per government over time
	//     chart: the governments ranked for the chosen year
	//     table: each government's change from the first year to the chosen year
	//
	// The choices live in the address (see lib/model/compare.ts): the page reads
	// them once it opens, and rewrites the address whenever one changes, so the
	// address always shares the comparison on screen.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Chart from '#lib/components/charts/Chart.svelte';
	import ChartFigure from '#lib/components/charts/ChartFigure.svelte';
	import DataTable from '#lib/components/charts/DataTable.svelte';
	import ChoiceGroup from '#lib/components/controls/ChoiceGroup.svelte';
	import GovernmentPicker from '#lib/components/controls/GovernmentPicker.svelte';
	import MeasureChoice from '#lib/components/controls/MeasureChoice.svelte';
	import SpendingSelect from '#lib/components/controls/SpendingSelect.svelte';
	import Switches from '#lib/components/controls/Switches.svelte';
	import YearSelect from '#lib/components/controls/YearSelect.svelte';
	import {
		barsAt,
		changeTable,
		figuresCsv,
		measureNotes,
		rankingTable,
		sourcesOf,
		trendTable,
		type Line
	} from '#lib/charts/figures.ts';
	import { rankingChart } from '#lib/charts/ranking.ts';
	import { highestPlaceTitle } from '#lib/charts/titles.ts';
	import { trendChart } from '#lib/charts/trend.ts';
	import { fiscalYearLabel } from '#lib/i18n/format.ts';
	import { localName, messages } from '#lib/i18n/index.ts';
	import {
		ALL_GOVERNMENTS,
		ALL_PROVINCES,
		MAX_COMPARED,
		TOTAL,
		compareFileFor,
		comparisonQuery,
		defaultComparison,
		readComparison,
		seriesFor,
		type CompareFile,
		type Comparison,
		type ProvinceView
	} from '#lib/model/compare.ts';
	import { FEDERAL, provincesAndTerritories } from '#lib/model/governments.ts';
	import { comparedName, functionName } from '#lib/model/names.ts';
	import type { SpendingSeries, Transfers } from '#lib/model/types.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const places = $derived(provincesAndTerritories(data.jurisdictions));
	const provinceCodes = $derived(places.map((place) => place.code));

	// --- The choices ------------------------------------------------------------

	const groups = $derived([
		{
			label: m.comparePage.groups.federal,
			options: [{ code: FEDERAL, label: m.federalGovernment }]
		},
		{
			label: m.comparePage.groups.provinces,
			options: places
				.filter((place) => place.kind === 'province')
				.map((place) => ({ code: place.code, label: localName(place, data.lang) }))
		},
		{
			label: m.comparePage.groups.territories,
			options: places
				.filter((place) => place.kind === 'territory')
				.map((place) => ({ code: place.code, label: localName(place, data.lang) }))
		},
		{
			label: m.comparePage.groups.combined,
			options: [
				{ code: ALL_PROVINCES, label: m.allProvinces },
				{ code: ALL_GOVERNMENTS, label: m.allGovernments }
			]
		}
	]);

	const allowed = $derived({
		governments: [FEDERAL, ...provinceCodes, ALL_PROVINCES, ALL_GOVERNMENTS],
		spending: [TOTAL, ...data.functions.map((each) => each.function_id)],
		years: data.years
	});

	// Built with the default comparison; the address's choices replace it once
	// the page opens in the browser (an address's query cannot be read while
	// pages are built ahead of time).
	let comparison: Comparison = $state(startingComparison());
	let addressRead = $state(false);

	function startingComparison(): Comparison {
		return defaultComparison(data.years);
	}

	onMount(() => {
		comparison = readComparison(new URLSearchParams(location.search), allowed);
		addressRead = true;
	});

	// Keep the address in step with the choices, without reloading the page
	// or adding a history entry for every click.
	$effect(() => {
		if (!addressRead) return;
		const query = comparisonQuery(comparison);
		if (location.search === `?${query}`) return;
		const address = `${resolve('/[lang=lang]/compare', { lang: data.lang })}?${query}`;
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved above, plus the query
		goto(address, { replace: true, shallow: true });
	});

	function choose(change: Partial<Comparison>) {
		comparison = { ...comparison, ...change };
	}

	// --- The data -----------------------------------------------------------------

	// Each data file, once loaded. Total spending is built into the page.
	let files: Record<string, SpendingSeries[]> = $state(builtInFiles());

	function builtInFiles(): Record<string, SpendingSeries[]> {
		return { [TOTAL]: data.total };
	}
	let loadFailed = $state(false);

	const parentOf = (id: string) =>
		data.functions.find((each) => each.function_id === id)?.parent_id ?? null;
	const fileName = $derived(compareFileFor(comparison.spending, parentOf));
	const series = $derived(files[fileName]);

	$effect(() => {
		const name = fileName;
		if (files[name]) return;
		loadFailed = false;
		fetch(resolve('/data/compare/[file].json', { file: name }))
			.then((response) => {
				if (!response.ok) throw new Error(`${response.status} for ${name}`);
				return response.json() as Promise<CompareFile>;
			})
			.then((content) => {
				files[name] = content.series;
			})
			.catch(() => {
				loadFailed = true;
			});
	});

	// --- What is shown ------------------------------------------------------------

	const measure = $derived(comparison.measure);
	const yearIndex = $derived(data.years.indexOf(comparison.year));
	const allYears = $derived(data.years.map((_, index) => index));
	const nameOf = (code: string) => comparedName(data.jurisdictions, code, data.lang);

	const lines: Line[] = $derived(
		series
			? comparison.governments.flatMap((code) => {
					const found = seriesFor(code, comparison, series);
					return found ? [{ label: nameOf(code), series: found, id: code }] : [];
				})
			: []
	);
	const missing = $derived(
		series
			? comparison.governments.filter((code) => !seriesFor(code, comparison, series)).map(nameOf)
			: []
	);
	const bars = $derived(barsAt(lines, yearIndex, measure));
	const rankedLines = $derived(bars.map((bar) => lines.find((line) => line.id === bar.id)!));

	const isSubFunction = $derived(parentOf(comparison.spending) !== null);
	const hasFederal = $derived(comparison.governments.includes(FEDERAL));
	const hasProvinces = $derived(
		comparison.governments.some((code) => provinceCodes.includes(code) || code === ALL_PROVINCES)
	);

	const spendingName = $derived(
		comparison.spending === TOTAL
			? m.comparePage.total
			: functionName(data.functions, comparison.spending, data.lang)
	);
	const trendTitle = $derived(
		m.titles.compareOverTime(
			spendingName,
			m.measurePhrases[measure],
			fiscalYearLabel(data.years[0], data.lang),
			fiscalYearLabel(data.years.at(-1)!, data.lang)
		)
	);
	const rankingTitle = $derived(
		highestPlaceTitle(spendingName, bars, measure, comparison.year, data.lang)
	);
	const changeHeading = $derived(
		m.comparePage.changeHeading(
			fiscalYearLabel(data.years[0], data.lang),
			fiscalYearLabel(comparison.year, data.lang)
		)
	);

	const notes = $derived([
		...(hasProvinces
			? [
					comparison.provinceView === 'province_wide'
						? m.viewNotes.province_wide
						: m.comparePage.provincialGovernmentNote
				]
			: []),
		...(hasFederal ? [m.transfersNotes[comparison.transfers]] : []),
		m.operatingOnly
	]);
	const sources = $derived(
		sourcesOf(
			lines.map((line) => line.series),
			data.sources
		)
	);
	const csvRows = $derived(
		figuresCsv(lines, data.years, m.government, measure, data.lang, data.sources)
	);
	const csvName = $derived(`compare-${comparison.spending}-${measure}.csv`);

	// --- Sharing ------------------------------------------------------------------

	let copyMessage = $state('');

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(location.href);
			copyMessage = m.comparePage.linkCopied;
		} catch {
			copyMessage = m.comparePage.copyFailed;
		}
	}

	const status = $derived.by(() => {
		if (loadFailed) return m.comparePage.loadFailed;
		if (!series) return m.comparePage.loading;
		if (missing.length > 0) return m.comparePage.noFigures(missing.join(', '));
		return '';
	});
</script>

<svelte:head>
	<title>{m.compareTitle} | {m.siteName}</title>
</svelte:head>

<h1>{m.compareTitle}</h1>
<p class="intro">{m.compareIntro}</p>

<Switches>
	<GovernmentPicker
		lang={data.lang}
		{groups}
		chosen={comparison.governments}
		max={MAX_COMPARED}
		onchange={(governments) => choose({ governments })}
	/>
	<SpendingSelect
		lang={data.lang}
		functions={data.functions}
		value={comparison.spending}
		onchange={(spending) => choose({ spending })}
	/>
	<MeasureChoice
		lang={data.lang}
		value={measure}
		onchange={(value) => choose({ measure: value })}
	/>
	{#if hasProvinces}
		<ChoiceGroup
			legend={m.comparePage.provinces}
			name="province-view"
			options={[
				{ value: 'province_wide', label: m.views.province_wide },
				{
					value: 'provincial_government',
					label: m.views.provincial_government,
					unavailableBecause: isSubFunction ? m.subFunctionsUnavailable : undefined
				}
			]}
			value={comparison.provinceView}
			onchange={(provinceView: ProvinceView) => choose({ provinceView })}
		/>
	{/if}
	{#if hasFederal}
		<ChoiceGroup
			legend={m.transfers}
			name="transfers"
			options={[
				{ value: 'included', label: m.transfersChoices.included },
				{
					value: 'excluded',
					label: m.transfersChoices.excluded,
					unavailableBecause: isSubFunction ? m.transfersOnlyForFunctions : undefined
				}
			]}
			value={comparison.transfers}
			onchange={(transfers: Transfers) => choose({ transfers })}
		/>
	{/if}
	<YearSelect
		lang={data.lang}
		years={data.years}
		value={comparison.year}
		onchange={(year) => choose({ year })}
	/>
	<div class="share">
		<button type="button" onclick={copyLink}>{m.comparePage.copyLink}</button>
		<span role="status">{copyMessage}</span>
	</div>
</Switches>

<p class="status" role="status">{status}</p>

{#if comparison.governments.length === 0}
	<p>{m.comparePage.noneChosen}</p>
{:else if lines.length > 0}
	<ChartFigure
		title={trendTitle}
		lang={data.lang}
		table={trendTable(lines, data.years, measure, data.lang)}
		{sources}
		notes={[
			...measureNotes(lines, data.years, allYears, measure, data.build.baseYear, data.lang),
			...notes
		]}
		csv={{ fileName: csvName, rows: csvRows }}
	>
		<Chart
			chart={(width) => trendChart(lines, data.years, measure, data.lang, width)}
			description={trendTitle}
		/>
	</ChartFigure>

	<ChartFigure
		title={rankingTitle}
		lang={data.lang}
		table={rankingTable(bars, m.government, measure, data.lang)}
		{sources}
		notes={[
			...measureNotes(lines, data.years, [yearIndex], measure, data.build.baseYear, data.lang),
			...notes
		]}
		csv={{ fileName: csvName, rows: csvRows }}
	>
		<Chart
			chart={(width) => rankingChart(bars, measure, data.lang, width)}
			description={rankingTitle}
		/>
	</ChartFigure>

	<section class="change" aria-labelledby="change-heading">
		<h2 id="change-heading">{changeHeading}</h2>
		<DataTable
			table={changeTable(rankedLines, data.years, 0, yearIndex, m.government, measure, data.lang)}
			caption={changeHeading}
			captionShown={false}
			lang={data.lang}
		/>
	</section>
{/if}

<style>
	.intro {
		font-size: 1.125rem;
		max-width: 48rem;
	}

	.share {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-s);
		padding: var(--space-s) 0;
	}

	.share button {
		font: inherit;
		padding: var(--space-xs) var(--space-s);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-background);
		color: var(--color-text);
		cursor: pointer;
	}

	.share span,
	.status {
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	/* Always present (empty when there is nothing to say), so screen readers
	   announce each new message. */
	.status {
		margin: 0 0 var(--space-m);
	}

	.change h2 {
		font-size: 1.25rem;
	}
</style>
