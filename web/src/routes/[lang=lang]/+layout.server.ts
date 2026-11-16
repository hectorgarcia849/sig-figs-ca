// Data every page in a language needs: the language, when the data was built,
// the years covered, the sources (for source lines), and the lists of
// governments and functions (for navigation and names).
import { readFunctions, readJurisdictions, readMeta } from '#lib/server/data.ts';
import { fiscalYears } from '#lib/server/series.ts';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ params }) => {
	const meta = readMeta();
	return {
		lang: params.lang,
		build: {
			builtAt: meta.built_at,
			baseYear: meta.base_year,
			firstFiscalYear: meta.first_fiscal_year,
			latestFiscalYear: meta.latest_fiscal_year
		},
		// Every series on every page lists one figure per year, in this order.
		years: fiscalYears(meta.first_fiscal_year, meta.latest_fiscal_year),
		sources: meta.sources,
		jurisdictions: readJurisdictions(),
		functions: readFunctions()
	};
};
