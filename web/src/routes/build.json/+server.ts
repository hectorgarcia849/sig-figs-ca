// /build.json: which approved build of the data the site shows, and which
// Statistics Canada release each source table is from. Lets anyone (and the
// checks after a deploy) confirm the live site shows the build that was approved.
import { json } from '@sveltejs/kit';
import { readMeta } from '#lib/server/data.ts';
import type { RequestHandler } from './$types';

export const prerender = true;

export const GET: RequestHandler = () => {
	const meta = readMeta();
	return json({
		build_id: meta.build_id,
		built_at: meta.built_at,
		first_fiscal_year: meta.first_fiscal_year,
		latest_fiscal_year: meta.latest_fiscal_year,
		releases: meta.sources.map(({ source_id, release }) => ({ source_id, release }))
	});
};
