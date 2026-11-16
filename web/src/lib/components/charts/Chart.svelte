<script lang="ts">
	// Shows a chart drawn by Observable Plot. The markup is made while the page
	// is built, so the chart is in the HTML from the start; in the browser it is
	// redrawn whenever its options change (e.g. a switch is used).
	//
	// In the dev server, Svelte warns "hydration_html_changed" on first load:
	// the browser writes the same chart with small differences (attribute order,
	// spaces). It keeps the built chart, which is what we want, and production
	// builds do not warn.
	import type * as Plot from '@observablehq/plot';
	import { drawChart } from '#lib/charts/draw.ts';

	let { options, description }: { options: Plot.PlotOptions; description: string } = $props();

	const markup = $derived(drawChart(options));
</script>

<!-- One image for screen readers, described in words; the table below the chart has every figure. -->
<div class="chart" role="img" aria-label={description}>
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
