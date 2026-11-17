/**
 * Ranking charts: horizontal bars, largest first, each labelled with its
 * figure. One bar can be highlighted (e.g. the province being viewed).
 */
import * as Plot from '@observablehq/plot';
import type { Bar } from './figures.ts';
import { revisionMark } from './figures.ts';
import { formatMeasure } from '#lib/i18n/format.ts';
import type { Language } from '#lib/i18n/index.ts';
import type { Measure } from '#lib/model/measures.ts';
import { BAR_COLOUR, CHART_WIDTH, HIGHLIGHT_COLOUR } from './draw.ts';

const BAR_HEIGHT = 28;
const AXIS_HEIGHT = 30;
const MARGIN_RIGHT = 90; // room for the figure after the longest bar

// Names longer than this are cut short with "…" (the table has them in full).
// On narrow screens names get at most this share of the width.
const LONGEST_NAME_CHARACTERS = 36;
const SHORTEST_NAME_CHARACTERS = 12;
const NAME_SHARE_OF_WIDTH = 0.35;
const PIXELS_PER_CHARACTER = 7.5; // at 12px text

/** The Plot options for a ranking chart (drawn with drawChart). */
export function rankingChart(
	bars: Bar[],
	measure: Measure,
	lang: Language,
	width = CHART_WIDTH
): Plot.PlotOptions {
	const shown = bars.filter((bar) => bar.value !== null);
	const nameRoom = Math.max(
		SHORTEST_NAME_CHARACTERS,
		Math.min(
			LONGEST_NAME_CHARACTERS,
			Math.floor((width * NAME_SHARE_OF_WIDTH) / PIXELS_PER_CHARACTER)
		)
	);
	const longestName = Math.min(Math.max(...shown.map((bar) => bar.label.length), 1), nameRoom);
	const figure = (bar: Bar) => {
		const mark = revisionMark(bar.revisionStatus, lang);
		return formatMeasure(measure, bar.value!, lang) + (mark ? ` ${mark}` : '');
	};

	return {
		width,
		height: shown.length * BAR_HEIGHT + AXIS_HEIGHT,
		marginLeft: Math.ceil(longestName * PIXELS_PER_CHARACTER) + 12,
		marginRight: MARGIN_RIGHT,
		x: {
			label: null,
			grid: true,
			axis: 'top',
			tickFormat: (value: number) => formatMeasure(measure, value, lang, 'axis')
		},
		y: { label: null, domain: shown.map((bar) => bar.label), tickSize: 0 },
		marks: [
			Plot.axisY({ textOverflow: 'ellipsis', lineWidth: nameRoom * 0.6 }),
			Plot.barX(shown, {
				x: 'value',
				y: 'label',
				fill: (bar: Bar) => (bar.highlight ? HIGHLIGHT_COLOUR : BAR_COLOUR),
				title: (bar: Bar) => `${bar.label}: ${figure(bar)}`
			}),
			Plot.ruleX([0]),
			Plot.text(shown, {
				x: 'value',
				y: 'label',
				text: figure,
				textAnchor: 'start',
				dx: 4,
				fill: 'currentColor'
			})
		]
	};
}
