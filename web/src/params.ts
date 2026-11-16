/**
 * Address checks: a folder named [lang=lang] only matches "en" or "fr".
 * Anything else (/de/..., /english/...) is not a page.
 */
import { defineParams } from '@sveltejs/kit/params';
import { isLanguage } from '#lib/i18n/index.ts';

export const params = defineParams({
	lang: (value) => (isLanguage(value) ? value : undefined)
});
