<script lang="ts">
	// One government's page.
	//
	// Federal: a switch for including or excluding transfers to other governments.
	// Province or territory: a switch between province-wide and provincial
	// government only; the latter also shows what municipalities received.
	import { choices } from '#lib/state/choices.svelte.ts';
	import KeyFigures from '#lib/components/KeyFigures.svelte';
	import SpendingOverview from '#lib/components/SpendingOverview.svelte';
	import ChoiceGroup from '#lib/components/controls/ChoiceGroup.svelte';
	import MeasureChoice from '#lib/components/controls/MeasureChoice.svelte';
	import Switches from '#lib/components/controls/Switches.svelte';
	import YearSelect from '#lib/components/controls/YearSelect.svelte';
	import { figureTile, type KeyFigure } from '#lib/charts/figures.ts';
	import { formatTotal } from '#lib/i18n/format.ts';
	import { FEDERAL } from '#lib/model/governments.ts';
	import { messages } from '#lib/i18n/index.ts';
	import { isInflationAdjusted } from '#lib/model/measures.ts';
	import { governmentName } from '#lib/model/names.ts';
	import { sumSeries } from '#lib/model/totals.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const name = $derived(governmentName(data.jurisdictions, data.code, data.lang));
	const isFederal = $derived(data.code === FEDERAL);
	const measure = $derived(choices.measure ?? 'amount');
	const year = $derived(choices.year ?? data.years.at(-1)!);
	const yearIndex = $derived(data.years.indexOf(year));
	const transfers = $derived(choices.transfers ?? 'included');
	const view = $derived(choices.provinceView ?? 'province_wide');

	// The series in the chosen view. For the federal government with
	// transfers excluded there are no sub-functions (see the note shown).
	const shown = $derived(
		isFederal
			? data.series.filter((each) => each.transfers === transfers)
			: data.series.filter((each) => each.view === view)
	);

	const extraFigures = $derived.by((): KeyFigure[] => {
		if (isFederal) {
			// How much of federal spending went to other governments that year.
			const functions = new Set(
				data.functions.filter((each) => each.level === 1).map((each) => each.function_id)
			);
			const included = data.series.filter(
				(each) => each.transfers === 'included' && functions.has(each.function_id)
			);
			const amounts = included.map((each) => each.transfers_to_governments[yearIndex]);
			if (amounts.some((amount) => amount === null)) return [];
			const sum = amounts.reduce((total: number, amount) => total + amount!, 0);
			const label = transfers === 'included' ? m.transferredToOthers : m.transferredLeftOut;
			return [{ label, value: formatTotal(sum, data.lang) }];
		}
		// Comparing with all provinces only makes sense province-wide: the
		// provincial government alone is a different thing to count.
		if (view !== 'province_wide') return [];
		const perPerson = isInflationAdjusted(measure) ? 'amount_real_per_person' : 'amount_per_person';
		return [
			figureTile(
				m.allProvincesPerPerson,
				sumSeries(data.allProvinces),
				perPerson,
				data.years,
				yearIndex,
				data.lang
			)
		];
	});

	const viewNote = $derived(isFederal ? m.transfersNotes[transfers] : m.viewNotes[view]);
	const municipal = $derived(
		!isFederal && view === 'provincial_government' && data.municipalTransfers.length > 0
			? figureTile(
					m.totalReceived,
					data.municipalTransfers[0],
					measure,
					data.years,
					yearIndex,
					data.lang
				)
			: null
	);
</script>

<svelte:head>
	<title>{name} | {m.siteName}</title>
</svelte:head>

<h1>{name}</h1>

<Switches note={viewNote}>
	{#if isFederal}
		<ChoiceGroup
			legend={m.transfers}
			name="transfers"
			options={[
				{ value: 'included', label: m.transfersChoices.included },
				{ value: 'excluded', label: m.transfersChoices.excluded }
			]}
			value={transfers}
			onchange={(value) => (choices.transfers = value)}
		/>
	{:else}
		<ChoiceGroup
			legend={m.counting}
			name="view"
			options={[
				{ value: 'province_wide', label: m.views.province_wide },
				{ value: 'provincial_government', label: m.views.provincial_government }
			]}
			value={view}
			onchange={(value) => (choices.provinceView = value)}
		/>
	{/if}
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
	{name}
	fileName={`${data.code}-${isFederal ? `transfers-${transfers}` : view}`}
	series={shown}
	functions={data.functions}
	years={data.years}
	sources={data.sources}
	baseYear={data.build.baseYear}
	{measure}
	{yearIndex}
	notes={[viewNote]}
	{extraFigures}
	subFunctionsUnavailable={isFederal && transfers === 'excluded'
		? m.transfersOnlyForFunctions
		: !isFederal && view === 'provincial_government'
			? m.subFunctionsUnavailable
			: undefined}
>
	{#snippet afterFigures()}
		{#if municipal}
			<section aria-labelledby="municipal">
				<h2 id="municipal">{m.municipalTransfers}</h2>
				<KeyFigures figures={[municipal]} />
				<p class="note">{m.municipalTransfersNote}</p>
			</section>
		{/if}
	{/snippet}
</SpendingOverview>

<style>
	.note {
		color: var(--color-muted);
		font-size: 0.875rem;
		max-width: 48rem;
		margin-bottom: var(--space-l);
	}
</style>
