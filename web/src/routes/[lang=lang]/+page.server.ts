// Home: Canada combined (all governments, each dollar counted once), and who spends it.
import { functionIds, readSpending } from '#lib/server/data.ts';
import { spendingSeries } from '#lib/server/series.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { years } = await parent();
	const functions = new Set(functionIds());
	const rows = readSpending();
	return {
		// Functions and sub-functions, all governments combined.
		canada: spendingSeries(
			rows.filter((row) => row.view === 'canada' && row.transfers === 'included'),
			years
		),
		// The two parts that add up to it: federal own spending and all provinces.
		federalOwn: spendingSeries(
			rows.filter((row) => row.view === 'federal' && row.transfers === 'excluded'),
			years
		),
		allProvinces: spendingSeries(
			rows.filter(
				(row) =>
					row.view === 'province_wide' &&
					row.jurisdiction === 'ca' &&
					row.transfers === 'included' &&
					functions.has(row.function_id)
			),
			years
		)
	};
};
