// /data/compare/<file>.json: the Compare page's data, one file for total
// spending and one per function (see lib/server/compare.ts). Built once, with the site.
import { error, json } from '@sveltejs/kit';
import { compareFile, compareFiles } from '#lib/server/compare.ts';
import { readMeta } from '#lib/server/data.ts';
import { fiscalYears } from '#lib/server/series.ts';
import type { EntryGenerator, RequestHandler } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => compareFiles().map((file) => ({ file }));

export const GET: RequestHandler = ({ params }) => {
	if (!compareFiles().includes(params.file)) error(404, `No compare file ${params.file}`);
	const meta = readMeta();
	return json(
		compareFile(params.file, fiscalYears(meta.first_fiscal_year, meta.latest_fiscal_year))
	);
};
