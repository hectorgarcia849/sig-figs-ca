/**
 * The switch settings a visitor has picked while browsing.
 *
 * Each setting stays empty until the visitor picks something; until then each
 * page uses its own default (dollars on government pages, per person on
 * function pages). Once picked, a setting carries over from page to page, so
 * "per person" on Ontario stays "per person" on Quebec.
 *
 * Kept in memory only: a full page load starts again from the defaults.
 * Only changed by the visitor in the browser, never while pages are built.
 */
import type { Measure } from '#lib/model/measures.ts';
import type { Transfers, View } from '#lib/model/types.ts';

export interface Choices {
	measure?: Measure;
	year?: number;
	provinceView?: Extract<View, 'province_wide' | 'provincial_government'>;
	transfers?: Transfers;
}

export const choices: Choices = $state({});
