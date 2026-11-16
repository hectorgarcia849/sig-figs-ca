// One function of government (health, education, ...) across governments.
import { error } from '@sveltejs/kit';
import { LANGUAGES } from '#lib/i18n/index.ts';
import { readFunctions, readSpending } from '#lib/server/data.ts';
import { spendingSeries } from '#lib/server/series.ts';
import type { EntryGenerator, PageServerLoad } from './$types';

/** The IDs of the 10 functions: "701" to "710". */
function functionIds(): string[] {
	return readFunctions()
		.filter((each) => each.level === 1)
		.map((each) => each.function_id);
}

// Every address to build: each language with each function.
export const entries: EntryGenerator = () =>
	LANGUAGES.flatMap((lang) => functionIds().map((id) => ({ lang, id })));

export const load: PageServerLoad = async ({ params, parent }) => {
	const { id } = params;
	const { years } = await parent();
	if (!functionIds().includes(id)) {
		error(404, `No function with ID ${id}`);
	}

	// The function and its sub-functions.
	const ids = new Set(
		readFunctions()
			.filter((each) => each.function_id === id || each.parent_id === id)
			.map((each) => each.function_id)
	);

	// Province-wide, to compare provinces fairly, and federal, with both transfers choices.
	return {
		id,
		series: spendingSeries(
			readSpending().filter(
				(row) =>
					ids.has(row.function_id) &&
					((row.view === 'province_wide' && row.transfers === 'included') || row.view === 'federal')
			),
			years
		)
	};
};
