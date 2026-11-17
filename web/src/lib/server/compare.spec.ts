import { describe, expect, it } from 'vitest';
import { TOTAL } from '#lib/model/compare.ts';
import type { SpendingRow } from '#lib/model/types.ts';
import { totalSeries } from './compare.ts';

function row(fields: Partial<SpendingRow>): SpendingRow {
	return {
		view: 'province_wide',
		jurisdiction: 'on',
		function_id: '701',
		fiscal_year: 2024,
		transfers: 'included',
		amount: 100,
		amount_real: 100,
		amount_per_person: 10,
		amount_real_per_person: 10,
		percent_of_gdp: 1,
		transfers_to_governments: 0,
		gdp_method: 'exact',
		revision_status: 'preliminary',
		release: '2025-11-27',
		source_id: 'statcan-10100005',
		vector: 'v701',
		...fields
	};
}

describe('totalSeries', () => {
	const years = [2024];
	const functions = ['701', '707'];

	it('adds the functions together for each government, view and transfers choice', () => {
		const rows = [
			row({}),
			row({ function_id: '707', amount: 300, amount_per_person: 30, vector: 'v707' }),
			row({ view: 'federal', jurisdiction: 'ca', transfers: 'excluded', amount: 5 }),
			row({
				view: 'federal',
				jurisdiction: 'ca',
				transfers: 'excluded',
				function_id: '707',
				amount: 7
			})
		];
		const totals = totalSeries(years, rows, functions);
		const ontario = totals.find((each) => each.jurisdiction === 'on')!;
		expect(ontario.function_id).toBe(TOTAL);
		expect(ontario.values.amount).toEqual([400]);
		expect(ontario.values.amount_per_person).toEqual([40]);
		expect(ontario.vector).toBe('v701+v707');
		const federal = totals.find((each) => each.view === 'federal')!;
		expect(federal.transfers).toBe('excluded');
		expect(federal.values.amount).toEqual([12]);
	});

	it('leaves out sub-functions, and governments missing a function', () => {
		const rows = [
			row({}),
			row({ function_id: '707', vector: 'v707' }),
			row({ function_id: '7073', vector: 'v7073', amount: 1000 }),
			row({ jurisdiction: 'qc', vector: 'vqc' })
		];
		const totals = totalSeries(years, rows, functions);
		expect(totals.map((each) => each.jurisdiction)).toEqual(['on']);
		expect(totals[0].values.amount).toEqual([200]);
	});
});
