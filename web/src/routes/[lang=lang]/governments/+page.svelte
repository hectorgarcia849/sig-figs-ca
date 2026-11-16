<script lang="ts">
	// The governments list: federal, then each province and territory, with
	// its total, per person and share of GDP in the latest year.
	import { resolve } from '$app/paths';
	import DataTable from '#lib/components/charts/DataTable.svelte';
	import { revisionMark, type TableData } from '#lib/figures.ts';
	import { fiscalYearLabel, formatMeasure } from '#lib/format.ts';
	import { messages } from '#lib/i18n/index.ts';
	import { governmentName } from '#lib/names.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const table = $derived<TableData>({
		columns: [m.government, m.totalSpending, m.perPerson, m.shareOfGdp],
		rows: data.governments.map((government) => {
			const mark = revisionMark(government.revisionStatus, data.lang);
			const cell = (
				measure: 'amount' | 'amount_per_person' | 'percent_of_gdp',
				value: number | null
			) =>
				value === null
					? { text: m.noFigure }
					: { text: formatMeasure(measure, value, data.lang), mark };
			return {
				header: governmentName(data.jurisdictions, government.code, data.lang),
				href: resolve('/[lang=lang]/governments/[code]', {
					lang: data.lang,
					code: government.code
				}),
				cells: [
					cell('amount', government.amount),
					cell('amount_per_person', government.perPerson),
					cell('percent_of_gdp', government.percentOfGdp)
				]
			};
		})
	});
</script>

<svelte:head>
	<title>{m.governmentsTitle} | {m.siteName}</title>
</svelte:head>

<h1>{m.governmentsTitle}</h1>
<p class="intro">{m.governmentsIntro}</p>

<DataTable
	{table}
	caption={`${m.governmentsTitle}, ${fiscalYearLabel(data.latestYear, data.lang)}`}
	lang={data.lang}
/>

<style>
	.intro {
		max-width: 48rem;
	}
</style>
