// The governments list: each government's total in the latest year.
import { FEDERAL, provincesAndTerritories } from '#lib/model/governments.ts';
import { functionIds, readJurisdictions, readSpending } from '#lib/server/data.ts';
import { spendingSeries } from '#lib/server/series.ts';
import { sumSeries } from '#lib/model/totals.ts';
import type { MeasureSeries } from '#lib/model/types.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { years } = await parent();
	const latest = years.length - 1;
	const functions = new Set(functionIds());
	const rows = readSpending().filter(
		(row) => row.transfers === 'included' && functions.has(row.function_id)
	);

	/** A government's total for the latest year, from its 10 functions. */
	function latestTotal(code: string, series: MeasureSeries[]) {
		const total = sumSeries(series);
		return {
			code,
			amount: total.values.amount[latest],
			perPerson: total.values.amount_per_person[latest],
			percentOfGdp: total.values.percent_of_gdp[latest],
			revisionStatus: total.revision_status[latest]
		};
	}

	return {
		latestYear: years[latest],
		governments: [
			latestTotal(
				FEDERAL,
				spendingSeries(
					rows.filter((row) => row.view === 'federal'),
					years
				)
			),
			...provincesAndTerritories(readJurisdictions()).map((place) =>
				latestTotal(
					place.code,
					spendingSeries(
						rows.filter((row) => row.view === 'province_wide' && row.jurisdiction === place.code),
						years
					)
				)
			)
		]
	};
};
