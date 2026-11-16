import { describe, expect, it } from 'vitest';
import type { SpendingRow } from '#lib/types.ts';
import { fiscalYears, spendingSeries } from './series.ts';

function row(fields: Partial<SpendingRow>): SpendingRow {
	return {
		view: 'federal',
		jurisdiction: 'ca',
		function_id: '707',
		fiscal_year: 2023,
		transfers: 'included',
		amount: 100,
		amount_real: 110,
		amount_per_person: 10,
		amount_real_per_person: 11,
		percent_of_gdp: 1.5,
		transfers_to_governments: 40,
		gdp_method: 'exact',
		revision_status: 'revised',
		release: '2025-11-27',
		source_id: 'statcan-10100024',
		vector: 'v1',
		...fields
	};
}

describe('fiscalYears', () => {
	it('lists every year from the first to the latest', () => {
		expect(fiscalYears(2022, 2024)).toEqual([2022, 2023, 2024]);
	});
});

describe('spendingSeries', () => {
	const years = [2022, 2023, 2024];

	it('lines each measure up with the years, leaving gaps empty', () => {
		const [series] = spendingSeries(
			[
				row({ fiscal_year: 2024, amount: 200, revision_status: 'preliminary' }),
				row({ fiscal_year: 2023 })
			],
			years
		);
		expect(series.values.amount).toEqual([null, 100, 200]);
		expect(series.revision_status).toEqual([null, 'revised', 'preliminary']);
		expect(series.transfers_to_governments).toEqual([null, 40, 40]);
		expect(series.vector).toBe('v1');
	});

	it('makes one series per view, jurisdiction, function and transfers choice', () => {
		const series = spendingSeries(
			[
				row({}),
				row({ transfers: 'excluded', vector: 'v1' }),
				row({ function_id: '7071', vector: 'v2' })
			],
			years
		);
		expect(series.map((each) => `${each.function_id} ${each.transfers}`)).toEqual([
			'707 included',
			'707 excluded',
			'7071 included'
		]);
	});

	it('refuses a series made from two vectors', () => {
		expect(() =>
			spendingSeries([row({}), row({ fiscal_year: 2024, vector: 'v9' })], years)
		).toThrow('one vector');
	});
});
