/**
 * Chart titles that state the main point, worked out from the figures.
 *
 * They only ever state facts (largest, highest, went from ... to ...), never
 * judgments, so the site stays non-partisan. Each follows a "subject: finding"
 * pattern that reads naturally in English and French.
 */
import type { Bar } from './figures.ts';
import { fiscalYearLabel, formatMeasure, formatPercent } from '#lib/i18n/format.ts';
import { messages, type Language } from '#lib/i18n/index.ts';
import type { Measure } from '#lib/model/measures.ts';
import type { MeasureSeries } from '#lib/model/types.ts';

/** "Spending per person went from $7,128 in 2008-09 to $12,626 in 2024-25". */
export function overTimeTitle(
	total: MeasureSeries,
	years: number[],
	yearIndex: number,
	measure: Measure,
	lang: Language
): string {
	const m = messages(lang);
	const values = total.values[measure];
	const firstIndex = values.findIndex((value) => value !== null);
	const last = values[yearIndex];
	if (firstIndex < 0 || last === null || firstIndex >= yearIndex) return m.titles.overTimePlain;
	return m.titles.overTime(
		m.measurePhrases[measure],
		formatMeasure(measure, values[firstIndex]!, lang),
		fiscalYearLabel(years[firstIndex], lang),
		formatMeasure(measure, last, lang),
		fiscalYearLabel(years[yearIndex], lang)
	);
}

/** "Largest area of spending in 2024-25: Social protection". Bars must be largest first. */
export function largestTitle(bars: Bar[], year: number, lang: Language): string {
	const m = messages(lang);
	const largest = bars.find((bar) => bar.value !== null);
	return largest
		? m.titles.largest(fiscalYearLabel(year, lang), largest.label)
		: m.titles.byFunctionPlain;
}

/** "Largest part of Health in 2024-25: Hospital services". Bars must be largest first. */
export function largestPartTitle(
	functionName: string,
	bars: Bar[],
	year: number,
	lang: Language
): string {
	const m = messages(lang);
	const largest = bars.find((bar) => bar.value !== null);
	return largest
		? m.titles.largestPart(functionName, fiscalYearLabel(year, lang), largest.label)
		: m.subFunctions;
}

/** "Health per person in 2024-25: highest in Nunavut". Bars must be largest first. */
export function highestPlaceTitle(
	functionName: string,
	bars: Bar[],
	measure: Measure,
	year: number,
	lang: Language
): string {
	const m = messages(lang);
	const highest = bars.find((bar) => bar.value !== null);
	return highest
		? m.titles.highestPlace(
				functionName,
				m.measurePhrases[measure],
				fiscalYearLabel(year, lang),
				highest.label
			)
		: functionName;
}

/** "Health in 2024-25: 96.2% spent by provinces and territories". */
export function provincesShareTitle(
	functionName: string,
	provinces: MeasureSeries,
	allGovernments: MeasureSeries,
	yearIndex: number,
	year: number,
	lang: Language
): string {
	const m = messages(lang);
	const part = provinces.values.amount[yearIndex];
	const whole = allGovernments.values.amount[yearIndex];
	if (part === null || whole === null || whole === 0) return m.whoDelivers;
	return m.titles.provincesShare(
		functionName,
		fiscalYearLabel(year, lang),
		formatPercent((part / whole) * 100, lang)
	);
}
