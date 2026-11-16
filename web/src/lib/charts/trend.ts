/**
 * Trend charts: one or more lines over the fiscal years.
 *
 * Preliminary and revised figures are open dots, marked "p" or "r". Hovering
 * over a year shows its figure (the table under the chart has every figure).
 */
import * as Plot from '@observablehq/plot';
import type { Line } from '#lib/figures.ts';
import { revisionMark } from '#lib/figures.ts';
import { fiscalYearLabel, formatMeasure } from '#lib/format.ts';
import type { Language } from '#lib/i18n/index.ts';
import type { Measure } from '#lib/measures.ts';
import { LINE_COLOURS } from './draw.ts';

const HEIGHT = 320;
const MARGIN_LEFT = 80; // room for labels such as "$1,137.1B"
const MARGIN_RIGHT = 40; // room for the last year's label, e.g. "2024-2025"
const YEARS_BETWEEN_TICKS = 4;

interface Point {
	line: string;
	year: number;
	value: number;
	mark?: string;
}

/** The Plot options for a trend chart (drawn with drawChart). */
export function trendChart(
	lines: Line[],
	years: number[],
	measure: Measure,
	lang: Language
): Plot.PlotOptions {
	const points: Point[] = lines.flatMap((line) =>
		years.flatMap((year, index) => {
			const value = line.series.values[measure][index];
			if (value === null) return [];
			return [
				{
					line: line.label,
					year,
					value,
					mark: revisionMark(line.series.revision_status[index], lang)
				}
			];
		})
	);
	const flagged = points.filter((point) => point.mark);
	const describe = (point: Point) =>
		`${point.line}, ${fiscalYearLabel(point.year, lang)}: ${formatMeasure(measure, point.value, lang)}`;
	const colour = lines.length > 1 ? 'line' : LINE_COLOURS[0];

	return {
		height: HEIGHT,
		marginLeft: MARGIN_LEFT,
		marginRight: MARGIN_RIGHT,
		x: {
			label: null,
			ticks: years.filter((year) => (years.at(-1)! - year) % YEARS_BETWEEN_TICKS === 0),
			tickFormat: (year: number) => fiscalYearLabel(year, lang)
		},
		y: {
			label: null,
			grid: true,
			zero: true,
			tickFormat: (value: number) => formatMeasure(measure, value, lang, 'axis')
		},
		color: {
			domain: lines.map((line) => line.label),
			range: LINE_COLOURS,
			legend: lines.length > 1
		},
		marks: [
			Plot.ruleY([0]),
			Plot.lineY(points, { x: 'year', y: 'value', z: 'line', stroke: colour, strokeWidth: 2 }),
			Plot.dot(flagged, { x: 'year', y: 'value', stroke: colour, fill: 'white', r: 3.5 }),
			Plot.text(flagged, { x: 'year', y: 'value', text: 'mark', dy: -10, fill: 'currentColor' }),
			// Invisible, wider targets so hovering near a year shows its figure.
			Plot.dot(points, {
				x: 'year',
				y: 'value',
				r: 8,
				fill: 'white',
				fillOpacity: 0,
				title: describe
			})
		]
	};
}
