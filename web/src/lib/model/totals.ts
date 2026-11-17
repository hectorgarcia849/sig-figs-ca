/**
 * Adding series together, e.g. the 10 functions into a government's total.
 *
 * Every measure adds up correctly, because the series added together belong
 * to one government: they share its population, its prices and its GDP. So
 * the total per person is the sum of the per-person figures, and so on.
 */
import { MEASURES, type Measure } from './measures.ts';
import type { MeasureSeries, RevisionStatus } from './types.ts';

/**
 * Series added year by year into one. A year is empty if any series is empty
 * that year (a partial total would mislead). It is preliminary if any part is
 * preliminary, revised if any part is revised, and its GDP is part-year if any
 * part's is.
 */
export function sumSeries(parts: MeasureSeries[]): MeasureSeries {
	const [first] = parts;
	const years = first.revision_status.length;
	const yearIndexes = Array.from({ length: years }, (_, index) => index);
	const sumAt = (measure: Measure, index: number) => {
		const values = parts.map((part) => part.values[measure][index]);
		return values.some((value) => value === null)
			? null
			: values.reduce((total: number, value) => total + value!, 0);
	};
	const values = Object.fromEntries(
		MEASURES.map((measure) => [measure, yearIndexes.map((index) => sumAt(measure, index))])
	) as MeasureSeries['values'];

	return {
		jurisdiction: first.jurisdiction,
		source_id: first.source_id,
		vector: parts.map((part) => part.vector).join('+'),
		values,
		revision_status: yearIndexes.map((index) =>
			leastFinal(parts.map((part) => part.revision_status[index]))
		),
		gdp_method: yearIndexes.map((index) => {
			const methods = parts.map((part) => part.gdp_method[index]);
			return methods.includes('partial') ? 'partial' : methods[0];
		})
	};
}

/** Preliminary if any figure is, otherwise revised if any is, otherwise not flagged. */
function leastFinal(statuses: RevisionStatus[]): RevisionStatus {
	if (statuses.includes('preliminary')) return 'preliminary';
	if (statuses.includes('revised')) return 'revised';
	return null;
}

/**
 * How a figure changed from the year before: a percentage change for money,
 * a change in percentage points for share of GDP. Null if either year is empty.
 */
export function changeFromYearBefore(
	series: MeasureSeries,
	measure: Measure,
	yearIndex: number
): number | null {
	return yearIndex < 1 ? null : changeBetween(series, measure, yearIndex - 1, yearIndex);
}

/**
 * How a figure changed between two years: a percentage change for money, a
 * change in percentage points for share of GDP. Null if either year is empty.
 */
export function changeBetween(
	series: MeasureSeries,
	measure: Measure,
	fromIndex: number,
	toIndex: number
): number | null {
	const now = series.values[measure][toIndex];
	const before = series.values[measure][fromIndex];
	if (now === null || before === null || before === 0) return null;
	return measure === 'percent_of_gdp' ? now - before : ((now - before) / before) * 100;
}
