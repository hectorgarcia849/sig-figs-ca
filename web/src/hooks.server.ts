/**
 * Runs while pages are built (and in the local dev server), never in the browser.
 *
 * 1. Gives charts a stand-in for the browser's page (linkedom), so Observable
 *    Plot can draw every chart straight into the built HTML.
 * 2. Sets <html lang="..."> on every page, so screen readers and search
 *    engines know which language it is in. The bilingual welcome page (/) is
 *    marked English, with its French parts marked lang="fr".
 */
import type { Handle, ServerInit } from '@sveltejs/kit/hooks';
import { parseHTML } from 'linkedom';
import { isLanguage } from '#lib/i18n/index.ts';

const WELCOME_PAGE_LANGUAGE = 'en';

export const init: ServerInit = () => {
	const { document } = parseHTML('<!doctype html><html><body></body></html>');
	globalThis.chartDocument = document as unknown as Document;
};

export const handle: Handle = ({ event, resolve }) => {
	const lang = event.params.lang ?? '';
	const pageLanguage = isLanguage(lang) ? lang : WELCOME_PAGE_LANGUAGE;
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%lang%', pageLanguage)
	});
};
