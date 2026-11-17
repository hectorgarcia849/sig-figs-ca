import { describe, expect, it } from 'vitest';
import type { Bar } from './figures.ts';
import { highestPlaceTitle, largestTitle, overTimeTitle, provincesShareTitle } from './titles.ts';
import type { MeasureSeries } from './types.ts';

function series(amounts: (number | null)[]): MeasureSeries {
	return {
		jurisdiction: 'ca',
		source_id: 'statcan-10100024',
		vector: 'v1',
		values: {
			amount: amounts,
			amount_real: amounts,
			amount_per_person: amounts,
			amount_real_per_person: amounts,
			percent_of_gdp: amounts
		},
		revision_status: amounts.map(() => null),
		gdp_method: amounts.map(() => 'exact')
	};
}

const bars = [
	{ label: 'Nunavut', value: 30_000 },
	{ label: 'Ontario', value: 5_738 }
] as Bar[];

describe('chart titles', () => {
	it('says how spending changed from the first year to the chosen one', () => {
		const total = series([null, 238.7e9, 519.7e9]);
		expect(overTimeTitle(total, [2007, 2008, 2024], 2, 'amount', 'en')).toBe(
			'Spending in dollars went from $238.7B in 2008-09 to $519.7B in 2024-25'
		);
		expect(overTimeTitle(total, [2007, 2008, 2024], 1, 'amount', 'en')).toBe('Spending over time');
	});

	it('names the largest function and the highest place', () => {
		expect(largestTitle(bars, 2024, 'fr')).toBe(
			'Principal domaine de dépenses en 2024-2025 : Nunavut'
		);
		expect(highestPlaceTitle('Health', bars, 'amount_per_person', 2024, 'en')).toBe(
			'Health per person in 2024-25: highest in Nunavut'
		);
	});

	it('gives the provinces’ share of a function', () => {
		const title = provincesShareTitle('Health', series([258.9]), series([269.1]), 0, 2024, 'en');
		expect(title).toBe('Health in 2024-25: 96.2% spent by provinces and territories');
	});
});
