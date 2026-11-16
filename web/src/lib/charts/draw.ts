/**
 * Draws a chart with Observable Plot and returns it as SVG markup.
 *
 * In the browser, Plot draws into the page as usual. While pages are built
 * there is no browser, so hooks.server.ts provides a lightweight stand-in
 * (linkedom) as globalThis.chartDocument. Either way the result is the same
 * markup, so every chart is already in the built HTML and the browser simply
 * redraws it when a switch changes.
 */
import * as Plot from '@observablehq/plot';

// Colours that stay distinct for colour-blind readers (Okabe and Ito).
export const LINE_COLOURS = [
	'#0072b2',
	'#e69f00',
	'#009e73',
	'#cc79a7',
	'#56b4e9',
	'#d55e00',
	'#000000'
];
export const BAR_COLOUR = '#1a5a96';
export const HIGHLIGHT_COLOUR = '#e69f00';

// Charts are drawn at this width and scale down to fit narrower screens.
export const CHART_WIDTH = 720;

// Text size in charts (Plot's own default, 10px, is hard to read).
const FONT_SIZE = '12px';

export function drawChart(options: Plot.PlotOptions): string {
	const document = globalThis.document ?? globalThis.chartDocument;
	if (!document) {
		throw new Error('No document to draw charts with (see hooks.server.ts).');
	}
	const chart = Plot.plot({
		width: CHART_WIDTH,
		style: { fontSize: FONT_SIZE },
		...options,
		document
	});
	removeInnerLabels(chart);
	return chart.outerHTML;
}

/**
 * Plot names each part of a chart for screen readers ("line", "dot", "rule"),
 * which is not valid on those parts and tells a listener nothing. The chart's
 * container (Chart.svelte) already describes the whole chart in one sentence,
 * and the table under each chart gives every figure, so the names are removed.
 */
function removeInnerLabels(chart: Element): void {
	for (const part of chart.querySelectorAll('[aria-label]')) {
		part.removeAttribute('aria-label');
	}
}
