/**
 * How numbers, years and dates are written, in Canadian English and French.
 *
 *     total dollars   $92.3B, $519.7M, $1,137.1B    92,3 G$, 519,7 M$, 1 137,1 G$
 *     per person      $5,738                         5 738 $
 *     share of GDP    7.6%                           7,6 %
 *     fiscal year     2024-25                        2024-2025
 *
 * Totals stay in billions from $1B up (never trillions), as in federal
 * budget documents, so amounts are easy to compare.
 */
import { LOCALES, type Language } from './i18n/index.ts';
import { isTotalDollars, type Measure } from './measures.ts';

const BILLION = 1_000_000_000;
const MILLION = 1_000_000;

// Decimal places shown.
const TOTAL_DECIMALS = 1;
const PERCENT_DECIMALS = 1;

// Units after billions and millions. French puts a no-break space before them.
const UNITS: Record<Language, { billions: string; millions: string }> = {
	en: { billions: 'B', millions: 'M' },
	fr: { billions: '\u00a0G$', millions: '\u00a0M$' }
};

/**
 * Figures always show their decimal ("$10.0B"), so a column of them lines up;
 * labels on chart axes drop a ".0" ("$10B"), which reads more easily.
 */
export type Style = 'figure' | 'axis';

function decimal(value: number, lang: Language, decimals: number, style: Style): string {
	return new Intl.NumberFormat(LOCALES[lang], {
		minimumFractionDigits: style === 'axis' ? 0 : decimals,
		maximumFractionDigits: decimals
	}).format(value);
}

/** Whole dollars: "$5,738" or "5 738 $". */
export function formatDollars(value: number, lang: Language): string {
	return new Intl.NumberFormat(LOCALES[lang], {
		style: 'currency',
		currency: 'CAD',
		currencyDisplay: 'narrowSymbol',
		maximumFractionDigits: 0
	}).format(value);
}

/** A total amount: "$92.3B", "$519.7M", or whole dollars below a million. */
export function formatTotal(value: number, lang: Language, style: Style = 'figure'): string {
	const size = Math.abs(value);
	if (size < MILLION) return formatDollars(value, lang);

	const [divisor, unit] =
		size >= BILLION ? [BILLION, UNITS[lang].billions] : [MILLION, UNITS[lang].millions];
	const number = decimal(Math.abs(value) / divisor, lang, TOTAL_DECIMALS, style);
	const sign = value < 0 ? '-' : '';
	return lang === 'en' ? `${sign}$${number}${unit}` : `${sign}${number}${unit}`;
}

/** A share given in percent (7.5998 means 7.5998%): "7.6%" or "7,6 %". */
export function formatPercent(value: number, lang: Language, style: Style = 'figure'): string {
	return new Intl.NumberFormat(LOCALES[lang], {
		style: 'percent',
		minimumFractionDigits: style === 'axis' ? 0 : PERCENT_DECIMALS,
		maximumFractionDigits: PERCENT_DECIMALS
	}).format(value / 100);
}

/** A value in whichever way its measure is written. */
export function formatMeasure(
	measure: Measure,
	value: number,
	lang: Language,
	style: Style = 'figure'
): string {
	if (measure === 'percent_of_gdp') return formatPercent(value, lang, style);
	if (isTotalDollars(measure)) return formatTotal(value, lang, style);
	return formatDollars(value, lang);
}

/** A fiscal year from its start year: 2024 is "2024-25" in English, "2024-2025" in French. */
export function fiscalYearLabel(startYear: number, lang: Language): string {
	const endYear = startYear + 1;
	return lang === 'en'
		? `${startYear}-${String(endYear % 100).padStart(2, '0')}`
		: `${startYear}-${endYear}`;
}

/** A count: "1,207" or "1 207". */
export function formatCount(value: number, lang: Language): string {
	return new Intl.NumberFormat(LOCALES[lang]).format(value);
}

/** A date such as "2025-11-27" in words: "November 27, 2025" or "27 novembre 2025". */
export function formatDate(isoDate: string, lang: Language): string {
	return new Intl.DateTimeFormat(LOCALES[lang], { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(`${isoDate.slice(0, 10)}T00:00:00Z`)
	);
}
