/**
 * The Compare page's choices, and how they are kept in the page's address.
 *
 * A comparison is a few governments, what spending to look at (total, a
 * function or a sub-function), a measure, a year and two switches. All of it
 * is in the address, so copying the address shares the comparison:
 *
 *     /en/compare?gov=on,qc,bc,ab&spending=707&measure=amount_per_person&year=2024
 *
 * Anything missing or not recognised in the address falls back to the default.
 */
import { FEDERAL, CANADA } from './governments.ts';
import { MEASURES, type Measure } from './measures.ts';
import type { SpendingSeries, Transfers, View } from './types.ts';

/** "Spending on" everything: the 10 functions added together. */
export const TOTAL = 'total';

/** Codes for the two combined lines that can be compared. */
export const ALL_PROVINCES = 'all-provinces';
export const ALL_GOVERNMENTS = 'all-governments';

/**
 * How many governments can be compared at once: the number of line colours
 * that stay distinct for colour-blind readers (see charts/draw.ts).
 */
export const MAX_COMPARED = 7;

/** The four largest provinces by population: a neutral starting point. */
export const DEFAULT_GOVERNMENTS = ['on', 'qc', 'bc', 'ab'];

// Per person by default: the fair way to compare governments of different sizes.
const DEFAULT_MEASURE: Measure = 'amount_per_person';

export type ProvinceView = Extract<View, 'province_wide' | 'provincial_government'>;

export interface Comparison {
	governments: string[]; // e.g. ["on", "qc", "federal", "all-provinces"]
	spending: string; // TOTAL, a function ("707") or a sub-function ("7073")
	measure: Measure;
	year: number;
	provinceView: ProvinceView;
	transfers: Transfers;
}

/** Names of the address's parts. */
const PARAMETERS = {
	governments: 'gov',
	spending: 'spending',
	measure: 'measure',
	year: 'year',
	provinceView: 'view',
	transfers: 'transfers'
} as const;

/** What one Compare data file holds (/data/compare/<file>.json). */
export interface CompareFile {
	file: string; // TOTAL or a function ID
	series: SpendingSeries[];
}

/** What a comparison may contain, from the data. */
export interface Allowed {
	governments: string[]; // every code that can be compared
	spending: string[]; // TOTAL and every function and sub-function ID
	years: number[];
}

/** The comparison shown before any choice is made. */
export function defaultComparison(years: number[]): Comparison {
	return {
		governments: DEFAULT_GOVERNMENTS,
		spending: TOTAL,
		measure: DEFAULT_MEASURE,
		year: years.at(-1)!,
		provinceView: 'province_wide',
		transfers: 'included'
	};
}

/** The comparison an address describes, with defaults for anything missing or unknown. */
export function readComparison(search: URLSearchParams, allowed: Allowed): Comparison {
	const fallback = defaultComparison(allowed.years);
	const given = (name: keyof typeof PARAMETERS) => search.get(PARAMETERS[name]);

	const governments = [
		...new Set(
			(given('governments') ?? '').split(',').filter((code) => allowed.governments.includes(code))
		)
	].slice(0, MAX_COMPARED);
	const spending = given('spending') ?? '';
	const measure = given('measure') as Measure;
	const year = Number(given('year'));
	const provinceView = given('provinceView');
	const transfers = given('transfers');

	return {
		governments: governments.length > 0 ? governments : fallback.governments,
		spending: allowed.spending.includes(spending) ? spending : fallback.spending,
		measure: MEASURES.includes(measure) ? measure : fallback.measure,
		year: allowed.years.includes(year) ? year : fallback.year,
		provinceView: provinceView === 'provincial_government' ? provinceView : fallback.provinceView,
		transfers: transfers === 'excluded' ? transfers : fallback.transfers
	};
}

/**
 * A comparison as the query part of an address, e.g. "gov=on,qc&spending=total&...".
 * The two switches are only written when they differ from their defaults.
 */
export function comparisonQuery(comparison: Comparison): string {
	const query = new URLSearchParams({
		[PARAMETERS.governments]: comparison.governments.join(','),
		[PARAMETERS.spending]: comparison.spending,
		[PARAMETERS.measure]: comparison.measure,
		[PARAMETERS.year]: String(comparison.year)
	});
	if (comparison.provinceView !== 'province_wide') {
		query.set(PARAMETERS.provinceView, comparison.provinceView);
	}
	if (comparison.transfers !== 'included') {
		query.set(PARAMETERS.transfers, comparison.transfers);
	}
	// Keep the commas readable in shared links ("on,qc" rather than "on%2Cqc").
	return query.toString().replaceAll('%2C', ',');
}

/**
 * The series that stands for one compared government, given the switches, or
 * undefined if the data has no such series (e.g. a sub-function for a
 * provincial government alone).
 *
 *     federal          the federal view, with or without transfers
 *     all-governments  all governments combined
 *     all-provinces    all provinces and territories, province-wide
 *     on, qc, ...      the province in the chosen province view
 */
export function seriesFor(
	code: string,
	comparison: Comparison,
	series: SpendingSeries[]
): SpendingSeries | undefined {
	const matches = (view: View, jurisdiction: string, transfers: Transfers = 'included') =>
		series.find(
			(each) =>
				each.function_id === comparison.spending &&
				each.view === view &&
				each.jurisdiction === jurisdiction &&
				each.transfers === transfers
		);

	if (code === FEDERAL) return matches('federal', CANADA, comparison.transfers);
	if (code === ALL_GOVERNMENTS) return matches('canada', CANADA);
	// All provinces combined exists only province-wide: provincial governments
	// alone cannot be added up per person (each has its own population).
	if (code === ALL_PROVINCES) {
		return comparison.provinceView === 'province_wide'
			? matches('province_wide', CANADA)
			: undefined;
	}
	return matches(comparison.provinceView, code);
}

/**
 * The query for a link into Compare from another page, e.g. from Ontario's
 * page: "gov=on,qc,bc,ab", or from health's page: "spending=707". Choices not
 * given take their defaults.
 */
export function startingQuery(start: { governments?: string[]; spending?: string }): string {
	const query = new URLSearchParams();
	if (start.governments) query.set(PARAMETERS.governments, start.governments.join(','));
	if (start.spending) query.set(PARAMETERS.spending, start.spending);
	return query.toString().replaceAll('%2C', ',');
}

/** A province or territory and the largest provinces after it: four in all. */
export function governmentsAlongside(code: string): string[] {
	return [code, ...DEFAULT_GOVERNMENTS.filter((each) => each !== code)].slice(
		0,
		DEFAULT_GOVERNMENTS.length
	);
}

/** The data file holding a choice of spending: total, or a function with its sub-functions. */
export function compareFileFor(spending: string, parentOf: (id: string) => string | null): string {
	return spending === TOTAL ? TOTAL : (parentOf(spending) ?? spending);
}
