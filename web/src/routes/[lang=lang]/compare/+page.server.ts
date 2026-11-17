// Compare governments. The page is built with total spending's data, so the
// default comparison is in the HTML from the start; other choices load their
// data file (/data/compare/<file>.json) in the browser.
import { TOTAL } from '#lib/model/compare.ts';
import { compareFile } from '#lib/server/compare.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { years } = await parent();
	return { total: compareFile(TOTAL, years).series };
};
