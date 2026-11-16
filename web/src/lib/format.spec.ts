import { describe, expect, it } from 'vitest';
import {
	fiscalYearLabel,
	formatCount,
	formatDate,
	formatDollars,
	formatMeasure,
	formatPercent,
	formatTotal
} from './format.ts';

// French formatting uses no-break spaces; compare with ordinary spaces.
const plain = (text: string) => text.replace(/[\u00a0\u202f]/g, ' ');

describe('totals', () => {
	it('stays in billions from $1B up', () => {
		expect(formatTotal(92_322_000_000, 'en')).toBe('$92.3B');
		expect(formatTotal(1_137_100_000_000, 'en')).toBe('$1,137.1B');
		expect(plain(formatTotal(1_137_100_000_000, 'fr'))).toBe('1 137,1 G$');
	});

	it('uses millions below a billion', () => {
		expect(formatTotal(519_700_000, 'en')).toBe('$519.7M');
		expect(plain(formatTotal(519_700_000, 'fr'))).toBe('519,7 M$');
	});

	it('uses whole dollars below a million, and keeps the sign', () => {
		expect(formatTotal(377_000, 'en')).toBe('$377,000');
		expect(formatTotal(-651_000_000, 'en')).toBe('-$651.0M');
	});
});

describe('other measures', () => {
	it('writes per-person amounts in whole dollars', () => {
		expect(formatDollars(5737.72, 'en')).toBe('$5,738');
		expect(plain(formatDollars(5737.72, 'fr'))).toBe('5 738 $');
	});

	it('writes shares of GDP with one decimal', () => {
		expect(formatPercent(7.5998, 'en')).toBe('7.6%');
		expect(plain(formatPercent(7.5998, 'fr'))).toBe('7,6 %');
	});

	it('drops a ".0" on chart axes only', () => {
		expect(formatTotal(10_000_000_000, 'en')).toBe('$10.0B');
		expect(formatTotal(10_000_000_000, 'en', 'axis')).toBe('$10B');
		expect(formatMeasure('percent_of_gdp', 5, 'en', 'axis')).toBe('5%');
	});

	it('picks the right style for each measure', () => {
		expect(formatMeasure('amount', 92_322_000_000, 'en')).toBe('$92.3B');
		expect(formatMeasure('amount_real_per_person', 5737.72, 'en')).toBe('$5,738');
		expect(formatMeasure('percent_of_gdp', 16.48, 'en')).toBe('16.5%');
	});
});

describe('years, counts and dates', () => {
	it('writes fiscal years in each language', () => {
		expect(fiscalYearLabel(2024, 'en')).toBe('2024-25');
		expect(fiscalYearLabel(2099, 'en')).toBe('2099-00');
		expect(fiscalYearLabel(2024, 'fr')).toBe('2024-2025');
	});

	it('writes counts and dates', () => {
		expect(plain(formatCount(1207, 'fr'))).toBe('1 207');
		expect(formatDate('2025-11-27', 'en')).toBe('November 27, 2025');
		expect(formatDate('2026-11-16T15:21:17', 'fr')).toBe('16 novembre 2026');
	});
});
