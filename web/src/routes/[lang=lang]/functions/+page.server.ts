// The functions list: all governments' spending on each function in the latest year.
import { readSpending } from '#lib/server/data.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { years, functions } = await parent();
	const latestYear = years.at(-1)!;
	const levelOne = new Set(
		functions.filter((each) => each.level === 1).map((each) => each.function_id)
	);
	const rows = readSpending().filter(
		(row) =>
			row.view === 'canada' &&
			row.transfers === 'included' &&
			row.fiscal_year === latestYear &&
			levelOne.has(row.function_id)
	);
	return {
		latestYear,
		figures: rows.map((row) => ({
			id: row.function_id,
			amount: row.amount,
			perPerson: row.amount_per_person,
			percentOfGdp: row.percent_of_gdp,
			revisionStatus: row.revision_status
		}))
	};
};
