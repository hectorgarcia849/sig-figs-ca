/**
 * Names of governments and functions in the page's language.
 *
 * Statistics Canada's own English and French labels are used, except where a
 * code means something different in a view: "ca" is Canada combined in the
 * "canada" view but all provinces and territories in the province-wide view.
 */
import { FEDERAL } from './governments.ts';
import { localName, messages, type Language } from '#lib/i18n/index.ts';
import type { GovernmentFunction, Jurisdiction, View } from './types.ts';

/** A function's name, e.g. "Health" or "Santé". */
export function functionName(
	functions: GovernmentFunction[],
	functionId: string,
	lang: Language
): string {
	const found = functions.find((each) => each.function_id === functionId);
	return found ? localName(found, lang) : functionId;
}

/** A government page's name: "Federal government", or a province or territory. */
export function governmentName(
	jurisdictions: Jurisdiction[],
	code: string,
	lang: Language
): string {
	if (code === FEDERAL) return messages(lang).federalGovernment;
	const found = jurisdictions.find((each) => each.code === code);
	return found ? localName(found, lang) : code;
}

/** The name for a jurisdiction within a view, so "ca" reads right in each. */
export function nameInView(
	jurisdictions: Jurisdiction[],
	view: View,
	code: string,
	lang: Language
): string {
	const m = messages(lang);
	if (view === 'federal') return m.federalGovernment;
	if (view === 'canada') return m.allGovernments;
	if (code === 'ca') return m.allProvinces;
	return governmentName(jurisdictions, code, lang);
}
