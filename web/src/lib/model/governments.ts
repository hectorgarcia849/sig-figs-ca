/**
 * The government pages and their addresses.
 *
 * There is one page for the federal government (/en/governments/federal) and
 * one for each province and territory (/en/governments/on, ...). "federal" is
 * used rather than "ca", because "ca" already stands for Canada combined and,
 * in the province-wide view, for all provinces and territories combined.
 */
import type { Jurisdiction } from './types.ts';

export const FEDERAL = 'federal';

/** Canada's jurisdiction code in the data. */
export const CANADA = 'ca';

/** Every government page's code: "federal", then each province and territory in order. */
export function governmentCodes(jurisdictions: Jurisdiction[]): string[] {
	return [FEDERAL, ...provincesAndTerritories(jurisdictions).map((place) => place.code)];
}

/** The 13 provinces and territories, in Statistics Canada's order (east to west, then north). */
export function provincesAndTerritories(jurisdictions: Jurisdiction[]): Jurisdiction[] {
	return jurisdictions.filter((place) => place.kind !== 'country');
}
