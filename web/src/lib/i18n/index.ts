/**
 * The two languages of the site, and how to get the interface text for each.
 *
 * Every address starts with the language: /en/... or /fr/...
 */
import { en, type Messages } from './en.ts';
import { fr } from './fr.ts';

export const LANGUAGES = ['en', 'fr'] as const;
export type Language = (typeof LANGUAGES)[number];

/** Canadian English and Canadian French, for formatting numbers and dates. */
export const LOCALES: Record<Language, string> = { en: 'en-CA', fr: 'fr-CA' };

const MESSAGES: Record<Language, Messages> = { en, fr };

/** Whether a piece of an address is one of our languages. */
export function isLanguage(value: string): value is Language {
	return (LANGUAGES as readonly string[]).includes(value);
}

/** The interface text for one language. */
export function messages(lang: Language): Messages {
	return MESSAGES[lang];
}

/** The language a page is not in: the target of the language switch. */
export function otherLanguage(lang: Language): Language {
	return lang === 'en' ? 'fr' : 'en';
}

/** A government's or function's name in one language, from Statistics Canada's labels. */
export function localName(item: { name_en: string; name_fr: string }, lang: Language): string {
	return lang === 'en' ? item.name_en : item.name_fr;
}

/** The same address in the other language: /en/governments/on becomes /fr/governments/on. */
export function addressInOtherLanguage(pathname: string, lang: Language): string {
	return pathname.replace(new RegExp(`^/${lang}(?=/|$)`), `/${otherLanguage(lang)}`);
}
