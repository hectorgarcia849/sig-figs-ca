<script lang="ts">
	// Shows a chart drawn by Observable Plot. The markup is made while the page
	// is built (at the standard width), so the chart is in the HTML from the
	// start. In the browser it is redrawn at the width actually available, so
	// text stays readable on phones, and whenever a switch changes.
	//
	// In the dev server, Svelte warns "hydration_html_changed" on first load:
	// the browser writes the same chart with small differences (attribute order,
	// spaces). It keeps the built chart, which is what we want, and production
	// builds do not warn.
	import type * as Plot from '@observablehq/plot';
	import { CHART_WIDTH, drawChart } from '#lib/charts/draw.ts';

	let {
		chart,
		description
	}: {
		chart: (width: number) => Plot.PlotOptions; // the chart's options at a given width
		description: string;
	} = $props();

	// The room the chart has: unknown while the page is built, then measured.
	let available = $state<number>();
	const width = $derived(available ? Math.min(available, CHART_WIDTH) : CHART_WIDTH);
	const markup = $derived(drawChart(chart(width)));
</script>

<!-- One image for screen readers, described in words; the table below the chart has every figure. -->
<div class="chart" role="img" aria-label={description} bind:clientWidth={available}>
	<!-- Markup made by Observable Plot from our own figures, not from visitors. -->
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html markup}
</div>

<style>
	.chart {
		overflow-x: auto;
	}

	.chart :global(svg) {
		max-width: 100%;
		height: auto;
	}

	/* The colour key above charts with several lines (Plot draws it at 10px). */
	.chart :global([class*='-swatches']) {
		font-size: 0.875rem;
	}
</style>
