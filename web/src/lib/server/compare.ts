/**
 * The Compare page's data files, made while the site is built.
 *
 * One file per function (/data/compare/707.json: health and its
 * sub-functions) and one for total spending (/data/compare/total.json). Each
 * holds every government in every view, for every year and measure, as the
 * same series the other pages receive, so Compare reuses their charts.
 *
 * The page loads only the file for the spending chosen: a few tens of
 * kilobytes, rather than all the data.
 */
import { TOTAL, type CompareFile } from '#lib/model/compare.ts';
import { sumSeries } from '#lib/model/totals.ts';
import type { SpendingRow, SpendingSeries } from '#lib/model/types.ts';
import { functionIds, readSpending, subFunctionIds } from './data.ts';
import { spendingSeries } from './series.ts';

/** Every data file's name: total, then each of the 10 functions. */
export function compareFiles(): string[] {
	return [TOTAL, ...functionIds()];
}

/** One data file's contents. */
export function compareFile(file: string, years: number[]): CompareFile {
	return { file, series: file === TOTAL ? totalSeries(years) : functionSeries(file, years) };
}

/** A function and its sub-functions, for every government, view and transfers choice. */
function functionSeries(functionId: string, years: number[]): SpendingSeries[] {
	const wanted = new Set([functionId, ...subFunctionIds(functionId)]);
	return spendingSeries(
		readSpending().filter((row) => wanted.has(row.function_id)),
		years
	);
}

/**
 * Total spending: the 10 functions added together, separately for every
 * government, view and transfers choice. Adding per-person figures is right
 * here because every part belongs to the same government (see totals.ts).
 */
export function totalSeries(
	years: number[],
	rows: SpendingRow[] = readSpending(),
	functions: string[] = functionIds()
): SpendingSeries[] {
	const wanted = new Set(functions);
	const byFunction = spendingSeries(
		rows.filter((row) => wanted.has(row.function_id)),
		years
	);
	const groups = new Map<string, SpendingSeries[]>();
	for (const series of byFunction) {
		const key = `${series.view}|${series.jurisdiction}|${series.transfers}`;
		groups.set(key, [...(groups.get(key) ?? []), series]);
	}
	return [...groups.values()]
		.filter((parts) => parts.length === wanted.size)
		.map((parts) => ({
			...sumSeries(parts),
			view: parts[0].view,
			function_id: TOTAL,
			transfers: parts[0].transfers,
			transfers_to_governments: years.map((_, index) => {
				const amounts = parts.map((part) => part.transfers_to_governments[index]);
				return amounts.some((amount) => amount === null)
					? null
					: amounts.reduce((sum: number, amount) => sum + amount!, 0);
			})
		}));
}
