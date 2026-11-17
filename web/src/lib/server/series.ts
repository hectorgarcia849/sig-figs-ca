/**
 * Turns exported rows (one per year) into series (one per line of figures over
 * time), which is how pages receive their data.
 *
 * A row repeats its view, government, function, source and vector for every
 * year; a series says them once and lists the year-by-year figures. That makes
 * each page's data about five times smaller.
 */
import type { Measure } from '#lib/model/measures.ts';
import type {
	MeasureSeries,
	Measures,
	MunicipalTransferRow,
	SpendingRow,
	SpendingSeries
} from '#lib/model/types.ts';

/** Every fiscal year from the first to the latest, oldest first: the years every series follows. */
export function fiscalYears(first: number, latest: number): number[] {
	return Array.from({ length: latest - first + 1 }, (_, index) => first + index);
}

/** Spending rows as series: one per view, jurisdiction, function and transfers choice. */
export function spendingSeries(rows: SpendingRow[], years: number[]): SpendingSeries[] {
	const groups = groupBy(
		rows,
		(row) => `${row.view}|${row.jurisdiction}|${row.function_id}|${row.transfers}`
	);
	return [...groups.values()].map((group) => {
		const [first] = group;
		const byYear = rowsByYear(group);
		return {
			view: first.view,
			function_id: first.function_id,
			transfers: first.transfers,
			...measureSeries(group, years),
			transfers_to_governments: years.map(
				(year) => byYear.get(year)?.transfers_to_governments ?? null
			)
		};
	});
}

/** Municipal transfer rows as series: one per province or territory. */
export function municipalSeries(rows: MunicipalTransferRow[], years: number[]): MeasureSeries[] {
	return [...groupBy(rows, (row) => row.jurisdiction).values()].map((group) =>
		measureSeries(group, years)
	);
}

/** What every series has: where it comes from, and each measure year by year. */
function measureSeries(
	group: (Measures & { jurisdiction: string; fiscal_year: number })[],
	years: number[]
): MeasureSeries {
	const [first] = group;
	const vectors = new Set(group.map((row) => row.vector));
	if (vectors.size !== 1) {
		throw new Error(`A series should come from one vector, but has ${[...vectors].join(', ')}`);
	}
	const byYear = rowsByYear(group);
	const valuesFor = (measure: Measure) => years.map((year) => byYear.get(year)?.[measure] ?? null);

	return {
		jurisdiction: first.jurisdiction,
		source_id: first.source_id,
		vector: first.vector,
		values: {
			amount: valuesFor('amount'),
			amount_real: valuesFor('amount_real'),
			amount_per_person: valuesFor('amount_per_person'),
			amount_real_per_person: valuesFor('amount_real_per_person'),
			percent_of_gdp: valuesFor('percent_of_gdp')
		},
		revision_status: years.map((year) => byYear.get(year)?.revision_status ?? null),
		gdp_method: years.map((year) => byYear.get(year)?.gdp_method ?? null)
	};
}

function rowsByYear<Row extends { fiscal_year: number }>(rows: Row[]): Map<number, Row> {
	return new Map(rows.map((row) => [row.fiscal_year, row]));
}

function groupBy<Row>(rows: Row[], key: (row: Row) => string): Map<string, Row[]> {
	const groups = new Map<string, Row[]>();
	for (const row of rows) {
		const name = key(row);
		groups.set(name, [...(groups.get(name) ?? []), row]);
	}
	return groups;
}
