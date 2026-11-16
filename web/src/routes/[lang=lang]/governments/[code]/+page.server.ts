// One government's page: the federal government, or a province or territory.
import { error } from '@sveltejs/kit';
import { FEDERAL, governmentCodes } from '#lib/governments.ts';
import { LANGUAGES } from '#lib/i18n/index.ts';
import { readJurisdictions, readMunicipalTransfers, readSpending } from '#lib/server/data.ts';
import type { EntryGenerator, PageServerLoad } from './$types';

// Every address to build: each language with each government.
export const entries: EntryGenerator = () =>
	LANGUAGES.flatMap((lang) => governmentCodes(readJurisdictions()).map((code) => ({ lang, code })));

export const load: PageServerLoad = ({ params }) => {
	const { code } = params;
	if (!governmentCodes(readJurisdictions()).includes(code)) {
		error(404, `No government with code ${code}`);
	}

	if (code === FEDERAL) {
		// Both transfers choices: the page can show spending with or without them.
		return {
			code,
			rows: readSpending().filter((row) => row.view === 'federal'),
			municipalTransfers: []
		};
	}

	// Province-wide and provincial government only. Transfers make no
	// difference to these, so the "included" rows are enough.
	return {
		code,
		rows: readSpending().filter(
			(row) =>
				row.jurisdiction === code &&
				(row.view === 'province_wide' || row.view === 'provincial_government') &&
				row.transfers === 'included'
		),
		municipalTransfers: readMunicipalTransfers().filter((row) => row.jurisdiction === code)
	};
};
