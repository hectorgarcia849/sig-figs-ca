// One function of government (health, education, ...) across governments.
import { error } from '@sveltejs/kit';
import { LANGUAGES } from '#lib/i18n/index.ts';
import { functionIds, readSpending, subFunctionIds } from '#lib/server/data.ts';
import { spendingSeries } from '#lib/server/series.ts';
import type { EntryGenerator, PageServerLoad } from './$types';

// Every address to build: each language with each function.
export const entries: EntryGenerator = () =>
	LANGUAGES.flatMap((lang) => functionIds().map((id) => ({ lang, id })));

export const load: PageServerLoad = async ({ params, parent }) => {
	const { id } = params;
	const { years } = await parent();
	if (!functionIds().includes(id)) {
		error(404, `No function with ID ${id}`);
	}
	const rows = readSpending();
	const functionAndParts = new Set([id, ...subFunctionIds(id)]);

	return {
		id,
		// Each province and territory, province-wide, plus all of them combined ("ca").
		provinces: spendingSeries(
			rows.filter(
				(row) =>
					row.view === 'province_wide' && row.function_id === id && row.transfers === 'included'
			),
			years
		),
		// The federal government's own spending on it, transfers to other governments excluded.
		federalOwn: spendingSeries(
			rows.filter(
				(row) => row.view === 'federal' && row.function_id === id && row.transfers === 'excluded'
			),
			years
		),
		// All governments combined, for the function and its sub-functions.
		allGovernments: spendingSeries(
			rows.filter(
				(row) =>
					row.view === 'canada' &&
					functionAndParts.has(row.function_id) &&
					row.transfers === 'included'
			),
			years
		)
	};
};
