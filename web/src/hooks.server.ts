/**
 * Sets <html lang="..."> on every page, so screen readers and search engines
 * know which language it is in. The bilingual welcome page (/) is marked
 * English, with its French parts marked lang="fr".
 */
import type { Handle } from '@sveltejs/kit/hooks';
import { isLanguage } from '#lib/i18n/index.ts';

const WELCOME_PAGE_LANGUAGE = 'en';

export const handle: Handle = ({ event, resolve }) => {
	const lang = event.params.lang ?? '';
	const pageLanguage = isLanguage(lang) ? lang : WELCOME_PAGE_LANGUAGE;
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%lang%', pageLanguage)
	});
};
