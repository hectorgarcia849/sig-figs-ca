// /robots.txt: every page may be read by search engines, and where the sitemap is.
import type { RequestHandler } from './$types';

export const prerender = true;

export const GET: RequestHandler = ({ url }) =>
	new Response(`User-agent: *\nAllow: /\n\nSitemap: ${url.origin}/sitemap.xml\n`, {
		headers: { 'Content-Type': 'text/plain' }
	});
