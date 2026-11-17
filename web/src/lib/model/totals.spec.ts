import { describe, expect, it } from 'vitest';
import { changeFromYearBefore, sumSeries } from './totals.ts';
import type { MeasureSeries } from './types.ts';

function series(amounts: (number | null)[], fields: Partial<MeasureSeries> = {}): MeasureSeries {
	return {
		jurisdiction: 'on',
		source_id: 'statcan-10100005',
		vector: 'v1',
		values: {
			amount: amounts,
			amount_real: amounts,
			amount_per_person: amounts.map((amount) => (amount === null ? null : amount / 10)),
			amount_real_per_person: amounts,
			percent_of_gdp: amounts.map((amount) => (amount === null ? null : amount / 100))
		},
		revision_status: [null, 'revised', 'preliminary'],
		gdp_method: ['exact', 'blended', 'blended'],
		...fields
	};
}

describe('sumSeries', () => {
	it('adds every measure year by year', () => {
		const total = sumSeries([series([100, 200, 300]), series([10, 20, 30], { vector: 'v2' })]);
		expect(total.values.amount).toEqual([110, 220, 330]);
		expect(total.values.amount_per_person).toEqual([11, 22, 33]);
		expect(total.values.percent_of_gdp).toEqual([1.1, 2.2, 3.3]);
		expect(total.vector).toBe('v1+v2');
	});

	it('leaves a year empty if any part is empty', () => {
		const total = sumSeries([series([100, null, 300]), series([10, 20, 30])]);
		expect(total.values.amount).toEqual([110, null, 330]);
	});

	it('keeps the least final status and part-year GDP', () => {
		const total = sumSeries([
			series([1, 2, 3], { revision_status: [null, null, 'revised'] }),
			series([1, 2, 3], { gdp_method: ['exact', 'exact', 'partial'] })
		]);
		expect(total.revision_status).toEqual([null, 'revised', 'preliminary']);
		expect(total.gdp_method).toEqual(['exact', 'blended', 'partial']);
	});
});

describe('changeFromYearBefore', () => {
	it('gives a percentage change for money and points for share of GDP', () => {
		const one = series([100, 110, 121]);
		expect(changeFromYearBefore(one, 'amount', 1)).toBeCloseTo(10);
		expect(changeFromYearBefore(one, 'percent_of_gdp', 2)).toBeCloseTo(0.11);
		expect(changeFromYearBefore(one, 'amount', 0)).toBeNull();
	});
});
