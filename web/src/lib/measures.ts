/**
 * The five measures every figure can be shown in. Their names match the
 * columns of spending_measures in schema/serving.sql.
 */

export const MEASURES = [
	'amount', // dollars, as spent that year
	'amount_real', // in base-year dollars, adjusted for inflation
	'amount_per_person',
	'amount_real_per_person',
	'percent_of_gdp'
] as const;

export type Measure = (typeof MEASURES)[number];

/** Whether a measure is a whole amount of money (shown in billions or millions). */
export function isTotalDollars(measure: Measure): boolean {
	return measure === 'amount' || measure === 'amount_real';
}

/** Whether a measure is adjusted for inflation. */
export function isInflationAdjusted(measure: Measure): boolean {
	return measure === 'amount_real' || measure === 'amount_real_per_person';
}
