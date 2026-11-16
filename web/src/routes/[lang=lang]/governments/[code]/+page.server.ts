// One government's page: the federal government, or a province or territory.
import { error } from '@sveltejs/kit';
import { FEDERAL, governmentCodes } from '#lib/governments.ts';
import { LANGUAGES } from '#lib/i18n/index.ts';
import {
	functionIds,
	readJurisdictions,
	readMunicipalTransfers,
	readSpending
} from '#lib/server/data.ts';
import { municipalSeries, spendingSeries } from '#lib/server/series.ts';
import type { EntryGenerator, PageServerLoad } from './$types';

// Every address to build: each language with each government.
export const entries: EntryGenerator = () =>
	LANGUAGES.flatMap((lang) => governmentCodes(readJurisdictions()).map((code) => ({ lang, code })));

export const load: PageServerLoad = async ({ params, parent }) => {
	const { code } = params;
	const { years } = await parent();
	if (!governmentCodes(readJurisdictions()).includes(code)) {
		error(404, `No government with code ${code}`);
	}
	const rows = readSpending();

	if (code === FEDERAL) {
		// Both transfers choices: the page shows spending with or without them.
		return {
			code,
			series: spendingSeries(
				rows.filter((row) => row.view === 'federal'),
				years
			),
			municipalTransfers: [],
			allProvinces: []
		};
	}

	// Province-wide and provincial government only (transfers make no
	// difference to these), what municipalities received, and all provinces
	// combined for comparison.
	const functions = new Set(functionIds());
	return {
		code,
		series: spendingSeries(
			rows.filter(
				(row) =>
					row.jurisdiction === code &&
					(row.view === 'province_wide' || row.view === 'provincial_government') &&
					row.transfers === 'included'
			),
			years
		),
		municipalTransfers: municipalSeries(
			readMunicipalTransfers().filter((row) => row.jurisdiction === code),
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
