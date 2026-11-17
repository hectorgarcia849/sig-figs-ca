import { parseHTML } from 'linkedom';
import { beforeAll, describe, expect, it } from 'vitest';
import { drawChart } from './draw.ts';
import { rankingChart } from './ranking.ts';
import { trendChart } from './trend.ts';
import { barsAt, changeTable, figuresCsv, measureNotes, trendTable, type Line } from './figures.ts';
import type { MeasureSeries, Source } from '#lib/model/types.ts';

const YEARS = [2022, 2023, 2024];

function series(amounts: (number | null)[], fields: Partial<MeasureSeries> = {}): MeasureSeries {
	return {
		jurisdiction: 'on',
		source_id: 'statcan-10100005',
		vector: 'v1',
		values: {
			amount: amounts,
			amount_real: amounts,
			amount_per_person: amounts.map((amount) => (amount === null ? null : amount / 100)),
			amount_real_per_person: amounts,
			percent_of_gdp: amounts.map(() => 5)
		},
		revision_status: [null, 'revised', 'preliminary'],
		gdp_method: ['exact', 'blended', 'partial'],
		...fields
	};
}

const LINES: Line[] = [
	{ label: 'Health', series: series([80e9, 85e9, 92.3e9]) },
	{ label: 'Education', series: series([40e9, null, 52.7e9], { vector: 'v2' }) }
];

const SOURCES = [{ source_id: 'statcan-10100005', table_number: '10-10-0005-01' } as Source];

describe('bars and tables', () => {
	it('ranks figures for one year, largest first, with gaps last', () => {
		const bars = barsAt([...LINES].reverse(), 1, 'amount');
		expect(bars.map((bar) => [bar.label, bar.value, bar.revisionStatus])).toEqual([
			['Health', 85e9, 'revised'],
			['Education', null, 'revised']
		]);
	});

	it('writes a trend as a table, newest year first, with marks', () => {
		const table = trendTable(LINES, YEARS, 'amount', 'en');
		expect(table.columns).toEqual(['Fiscal year', 'Health', 'Education']);
		expect(table.rows[0]).toEqual({
			header: '2024-25',
			cells: [
				{ text: '$92.3B', mark: 'p' },
				{ text: '$52.7B', mark: 'p' }
			]
		});
		expect(table.rows[1].cells[1]).toEqual({ text: 'no figure' });
	});

	it('writes the change between two years: percent for money, points for share of GDP', () => {
		const table = changeTable(LINES, YEARS, 0, 2, 'Function', 'amount', 'en');
		expect(table.columns).toEqual(['Function', '2022-23', '2024-25', 'Change']);
		expect(table.rows[0]).toEqual({
			header: 'Health',
			cells: [{ text: '$80.0B' }, { text: '$92.3B', mark: 'p' }, { text: '+15.4%' }]
		});
		const shares = changeTable(LINES, YEARS, 0, 2, 'Function', 'percent_of_gdp', 'en');
		expect(shares.rows[0].cells[2].text).toBe('0.0 percentage points');
	});

	it('has no change where a year has no figure', () => {
		const table = changeTable(LINES, YEARS, 1, 2, 'Function', 'amount', 'en');
		expect(table.rows[1].cells[2]).toEqual({ text: 'no figure' });
	});
});

describe('CSV and notes', () => {
	it('lists exact figures with their source table and vector', () => {
		const rows = figuresCsv(LINES, YEARS, 'Function', 'amount', 'en', SOURCES);
		expect(rows[0]).toEqual([
			'Fiscal year',
			'Function',
			'Dollars',
			'Revision status',
			'Statistics Canada table',
			'Vector'
		]);
		expect(rows[3]).toEqual(['2024-25', 'Health', 92.3e9, 'preliminary', '10-10-0005-01', 'v1']);
		expect(rows.length).toBe(1 + 2 * 3);
	});

	it('explains real dollars and part-year GDP', () => {
		expect(measureNotes(LINES, YEARS, [0, 1, 2], 'amount_real', 2024, 'en')).toEqual([
			"In 2024-25 dollars, adjusted for inflation with each government's own consumer price index."
		]);
		const gdpNotes = measureNotes(LINES, YEARS, [2], 'percent_of_gdp', 2024, 'en');
		expect(gdpNotes).toHaveLength(1);
		expect(gdpNotes[0]).toContain('2024-25');
		expect(measureNotes(LINES, YEARS, [0], 'percent_of_gdp', 2024, 'en')).toEqual([]);
	});
});

describe('drawing charts while pages are built', () => {
	beforeAll(() => {
		globalThis.chartDocument = parseHTML('<!doctype html><html><body></body></html>')
			.document as unknown as Document;
	});

	it('draws a trend chart with a legend, marks and hover text', () => {
		const markup = drawChart(trendChart(LINES, YEARS, 'amount', 'fr'));
		expect(markup).toContain('<svg');
		expect(markup).toContain('Health'); // in the legend
		expect(markup).toContain('<title>Health, 2024-2025: 92,3&#160;G$</title>');
		expect(markup).toContain('>50&#160;G$<'); // axis labels drop ",0"
	});

	it('draws a ranking chart with each figure after its bar', () => {
		const markup = drawChart(rankingChart(barsAt(LINES, 2, 'amount'), 'amount', 'en'));
		expect(markup).toContain('$92.3B p');
		expect(markup).toContain('$52.7B p');
	});

	it('leaves out Plot’s names for chart parts (the chart is described as a whole)', () => {
		expect(drawChart(trendChart(LINES, YEARS, 'amount', 'en'))).not.toContain('aria-label');
		expect(drawChart(rankingChart(barsAt(LINES, 2, 'amount'), 'amount', 'en'))).not.toContain(
			'aria-label'
		);
	});
});
