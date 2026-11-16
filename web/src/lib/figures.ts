/**
 * What every chart is made of, in one shape that the chart, its table, its
 * notes and its CSV download all read from, so they always show the same
 * figures.
 *
 *     Line   one series drawn over the years (trend charts)
 *     Bar    one series at one year (ranking charts)
 */
import type { CsvValue } from './csv.ts';
import { fiscalYearLabel, formatMeasure } from './format.ts';
import { messages, type Language } from './i18n/index.ts';
import { isInflationAdjusted, type Measure } from './measures.ts';
import type { MeasureSeries, RevisionStatus, Source } from './types.ts';

/** A series with the name it is shown under, e.g. "Health" or "Ontario". */
export interface Line {
	label: string;
	series: MeasureSeries;
}

/** One line's figure at one year. */
export interface Bar {
	label: string;
	value: number | null;
	revisionStatus: RevisionStatus;
	series: MeasureSeries;
	highlight?: boolean; // drawn in a different colour, e.g. the province being viewed
}

/** A table: column names, then one row per item (its name, then its cells). */
export interface TableData {
	columns: string[];
	rows: { header: string; cells: { text: string; mark?: string }[] }[];
}

/** Each line's figure at one year, largest first. Lines with no figure go last. */
export function barsAt(lines: Line[], yearIndex: number, measure: Measure): Bar[] {
	return lines
		.map((line) => ({
			label: line.label,
			value: line.series.values[measure][yearIndex],
			revisionStatus: line.series.revision_status[yearIndex],
			series: line.series
		}))
		.sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity));
}

/** "p" for preliminary, "r" for revised, nothing otherwise. */
export function revisionMark(status: RevisionStatus, lang: Language): string | undefined {
	const m = messages(lang);
	if (status === 'preliminary') return m.preliminaryMark;
	if (status === 'revised') return m.revisedMark;
	return undefined;
}

// --- Tables -----------------------------------------------------------------

/** A trend chart as a table: one row per year (newest first), one column per line. */
export function trendTable(
	lines: Line[],
	years: number[],
	measure: Measure,
	lang: Language
): TableData {
	const m = messages(lang);
	return {
		columns: [m.fiscalYear, ...lines.map((line) => line.label)],
		rows: years
			.map((year, index) => ({
				header: fiscalYearLabel(year, lang),
				cells: lines.map((line) =>
					cell(
						line.series.values[measure][index],
						line.series.revision_status[index],
						measure,
						lang
					)
				)
			}))
			.reverse()
	};
}

/** A ranking chart as a table: one row per bar, largest first. */
export function rankingTable(
	bars: Bar[],
	nameColumn: string,
	measure: Measure,
	lang: Language
): TableData {
	return {
		columns: [nameColumn, messages(lang).measures[measure]],
		rows: bars.map((bar) => ({
			header: bar.label,
			cells: [cell(bar.value, bar.revisionStatus, measure, lang)]
		}))
	};
}

function cell(value: number | null, status: RevisionStatus, measure: Measure, lang: Language) {
	if (value === null) return { text: messages(lang).noFigure };
	return { text: formatMeasure(measure, value, lang), mark: revisionMark(status, lang) };
}

// --- CSV downloads ----------------------------------------------------------

/**
 * Figures as CSV rows: one row per line and year, with the exact value (not
 * rounded for display), its revision status, and where it comes from.
 */
export function figuresCsv(
	lines: Line[],
	years: number[],
	nameColumn: string,
	measure: Measure,
	lang: Language,
	sources: Source[]
): CsvValue[][] {
	const m = messages(lang);
	const tableNumber = new Map(sources.map((source) => [source.source_id, source.table_number]));
	const header = [
		m.fiscalYear,
		nameColumn,
		m.measures[measure],
		m.revisionStatus,
		m.sourceTable,
		m.vector
	];
	const rows = lines.flatMap((line) =>
		years.map((year, index) => [
			fiscalYearLabel(year, lang),
			line.label,
			line.series.values[measure][index],
			line.series.revision_status[index],
			tableNumber.get(line.series.source_id) ?? line.series.source_id,
			line.series.vector
		])
	);
	return [header, ...rows];
}

// --- Notes and sources ------------------------------------------------------

/**
 * The notes a chart needs for the figures it shows: which dollars real
 * figures are in, and where share of GDP rests on part-year GDP.
 */
export function measureNotes(
	lines: Line[],
	years: number[],
	shownYearIndexes: number[],
	measure: Measure,
	baseYear: number,
	lang: Language
): string[] {
	const m = messages(lang);
	const notes: string[] = [];
	if (isInflationAdjusted(measure)) {
		notes.push(m.inBaseYearDollars(fiscalYearLabel(baseYear, lang)));
	}
	if (measure === 'percent_of_gdp') {
		const partial = shownYearIndexes.filter((index) =>
			lines.some((line) => line.series.gdp_method[index] === 'partial')
		);
		for (const index of partial) {
			notes.push(m.partialGdp(fiscalYearLabel(years[index], lang)));
		}
	}
	return notes;
}

/** The sources behind some series, each listed once. */
export function sourcesOf(series: MeasureSeries[], sources: Source[]): Source[] {
	const used = new Set(series.map((each) => each.source_id));
	return sources.filter((source) => used.has(source.source_id));
}
