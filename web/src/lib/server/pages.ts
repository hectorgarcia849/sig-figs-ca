/**
 * Every page address of the site, for the sitemap and the page checks.
 *
 * Each address is built for both languages: /en/... and /fr/...
 */
import { governmentCodes } from '#lib/model/governments.ts';
import { LANGUAGES, type Language } from '#lib/i18n/index.ts';
import { functionIds, readJurisdictions } from './data.ts';

/** Every page in one language, e.g. /en, /en/governments, /en/governments/on. */
export function pageAddresses(lang: Language): string[] {
	return [
		`/${lang}`,
		`/${lang}/governments`,
		...governmentCodes(readJurisdictions()).map((code) => `/${lang}/governments/${code}`),
		`/${lang}/functions`,
		...functionIds().map((id) => `/${lang}/functions/${id}`),
		`/${lang}/methodology`,
		`/${lang}/privacy`
	];
}

/** Every page of the site: the welcome page, then each language's pages. */
export function allPageAddresses(): string[] {
	return ['/', ...LANGUAGES.flatMap(pageAddresses)];
}
