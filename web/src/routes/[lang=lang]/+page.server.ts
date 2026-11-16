// Home: Canada combined (all governments, each dollar counted once).
import { readSpending } from '#lib/server/data.ts';
import { spendingSeries } from '#lib/server/series.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { years } = await parent();
	const rows = readSpending().filter(
		(row) => row.view === 'canada' && row.transfers === 'included'
	);
	return { series: spendingSeries(rows, years) };
};
