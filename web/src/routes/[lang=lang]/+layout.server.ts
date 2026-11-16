// Data every page in a language needs: the language, when the data was built,
// and the lists of governments and functions (for navigation and names).
import { readFunctions, readJurisdictions, readMeta } from '#lib/server/data.ts';
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
		jurisdictions: readJurisdictions(),
		functions: readFunctions()
	};
};
