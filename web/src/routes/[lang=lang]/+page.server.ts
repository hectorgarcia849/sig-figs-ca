// Home: Canada combined (all governments, each dollar counted once).
import { readSpending } from '#lib/server/data.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => ({
	rows: readSpending().filter((row) => row.view === 'canada' && row.transfers === 'included')
});
