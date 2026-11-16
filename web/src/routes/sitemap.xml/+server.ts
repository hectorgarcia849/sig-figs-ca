// /sitemap.xml: every page, so search engines find them all. Built once, with the site.
import { allPageAddresses } from '#lib/server/pages.ts';
import type { RequestHandler } from './$types';

export const prerender = true;

export const GET: RequestHandler = ({ url }) => {
	const entries = allPageAddresses()
		.map((address) => `  <url><loc>${url.origin}${address}</loc></url>`)
		.join('\n');
	const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries}
</urlset>
`;
	return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
};
