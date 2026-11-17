<script lang="ts">
	// The functions list: the 10 functions of government, with what all
	// governments spent on each in the latest year.
	import { resolve } from '$app/paths';
	import DataTable from '#lib/components/charts/DataTable.svelte';
	import { revisionMark, type TableData } from '#lib/charts/figures.ts';
	import { fiscalYearLabel, formatMeasure } from '#lib/i18n/format.ts';
	import { messages } from '#lib/i18n/index.ts';
	import { functionName } from '#lib/model/names.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const table = $derived<TableData>({
		columns: [m.function, m.totalSpending, m.perPerson, m.shareOfGdp],
		rows: data.functions
			.filter((each) => each.level === 1)
			.map((each) => {
				const figures = data.figures.find((figure) => figure.id === each.function_id);
				const mark = figures ? revisionMark(figures.revisionStatus, data.lang) : undefined;
				return {
					header: functionName(data.functions, each.function_id, data.lang),
					href: resolve('/[lang=lang]/functions/[id]', { lang: data.lang, id: each.function_id }),
					cells: figures
						? [
								{ text: formatMeasure('amount', figures.amount, data.lang), mark },
								{ text: formatMeasure('amount_per_person', figures.perPerson, data.lang), mark },
								{ text: formatMeasure('percent_of_gdp', figures.percentOfGdp, data.lang), mark }
							]
						: [{ text: m.noFigure }, { text: m.noFigure }, { text: m.noFigure }]
				};
			})
	});
</script>

<svelte:head>
	<title>{m.functionsTitle} | {m.siteName}</title>
</svelte:head>

<h1>{m.functionsTitle}</h1>
<p class="intro">{m.functionsIntro}</p>

<DataTable
	{table}
	caption={`${m.allGovernments}, ${fiscalYearLabel(data.latestYear, data.lang)}`}
	lang={data.lang}
/>

<style>
	.intro {
		max-width: 48rem;
	}
</style>
