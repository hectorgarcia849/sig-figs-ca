import { describe, expect, it } from 'vitest';
import {
	ALL_GOVERNMENTS,
	ALL_PROVINCES,
	DEFAULT_GOVERNMENTS,
	MAX_COMPARED,
	TOTAL,
	compareFileFor,
	comparisonQuery,
	defaultComparison,
	governmentsAlongside,
	readComparison,
	seriesFor,
	startingQuery,
	type Comparison
} from './compare.ts';
import type { SpendingSeries } from './types.ts';

const YEARS = [2022, 2023, 2024];
const ALLOWED = {
	governments: [
		'federal',
		'nl',
		'qc',
		'on',
		'mb',
		'sk',
		'ab',
		'bc',
		'nu',
		ALL_PROVINCES,
		ALL_GOVERNMENTS
	],
	spending: [TOTAL, '707', '7073'],
	years: YEARS
};

const read = (query: string) => readComparison(new URLSearchParams(query), ALLOWED);

describe('readComparison', () => {
	it('uses the defaults when the address has no choices', () => {
		expect(read('')).toEqual(defaultComparison(YEARS));
		expect(read('').governments).toEqual(DEFAULT_GOVERNMENTS);
		expect(read('').year).toBe(2024);
		expect(read('').measure).toBe('amount_per_person');
	});

	it('reads every choice', () => {
		expect(
			read(
				'gov=on,federal&spending=7073&measure=percent_of_gdp&year=2023&view=provincial_government&transfers=excluded'
			)
		).toEqual({
			governments: ['on', 'federal'],
			spending: '7073',
			measure: 'percent_of_gdp',
			year: 2023,
			provinceView: 'provincial_government',
			transfers: 'excluded'
		});
	});

	it('drops unknown and repeated governments, and keeps at most the maximum', () => {
		expect(read('gov=on,xx,on,qc').governments).toEqual(['on', 'qc']);
		const many = ALLOWED.governments.join(',');
		expect(read(`gov=${many}`).governments).toHaveLength(MAX_COMPARED);
	});

	it('falls back to the default for anything not recognised', () => {
		const comparison = read('gov=xx&spending=999&measure=votes&year=1990&view=x&transfers=x');
		expect(comparison).toEqual(defaultComparison(YEARS));
	});
});

describe('comparisonQuery', () => {
	it('writes the choices with readable commas, and the switches only when changed', () => {
		const comparison = defaultComparison(YEARS);
		expect(comparisonQuery(comparison)).toBe(
			'gov=on,qc,bc,ab&spending=total&measure=amount_per_person&year=2024'
		);
		const changed = { ...comparison, provinceView: 'provincial_government', transfers: 'excluded' };
		expect(comparisonQuery(changed as Comparison)).toBe(
			'gov=on,qc,bc,ab&spending=total&measure=amount_per_person&year=2024&view=provincial_government&transfers=excluded'
		);
	});

	it('is read back as the same comparison', () => {
		const comparison: Comparison = {
			governments: ['nu', ALL_PROVINCES, 'federal'],
			spending: '7073',
			measure: 'amount_real',
			year: 2022,
			provinceView: 'provincial_government',
			transfers: 'excluded'
		};
		expect(read(comparisonQuery(comparison))).toEqual(comparison);
	});
});

describe('links into Compare', () => {
	it('starts from a province and the largest provinces after it', () => {
		expect(governmentsAlongside('nu')).toEqual(['nu', 'on', 'qc', 'bc']);
		expect(governmentsAlongside('qc')).toEqual(['qc', 'on', 'bc', 'ab']);
	});

	it('writes only the choices given', () => {
		expect(startingQuery({ spending: '707' })).toBe('spending=707');
		expect(startingQuery({ governments: ['nu', 'on'] })).toBe('gov=nu,on');
	});
});

describe('seriesFor', () => {
	const series = (fields: Partial<SpendingSeries>) =>
		({
			view: 'province_wide',
			jurisdiction: 'on',
			function_id: TOTAL,
			transfers: 'included',
			...fields
		}) as SpendingSeries;
	const all = [
		series({}),
		series({ view: 'provincial_government' }),
		series({ jurisdiction: 'ca' }),
		series({ view: 'canada', jurisdiction: 'ca' }),
		series({ view: 'federal', jurisdiction: 'ca' }),
		series({ view: 'federal', jurisdiction: 'ca', transfers: 'excluded' })
	];
	const comparison = defaultComparison(YEARS);

	it('finds each government in the chosen view', () => {
		expect(seriesFor('on', comparison, all)).toBe(all[0]);
		expect(seriesFor('on', { ...comparison, provinceView: 'provincial_government' }, all)).toBe(
			all[1]
		);
		expect(seriesFor(ALL_PROVINCES, comparison, all)).toBe(all[2]);
		expect(seriesFor(ALL_GOVERNMENTS, comparison, all)).toBe(all[3]);
		expect(seriesFor('federal', comparison, all)).toBe(all[4]);
		expect(seriesFor('federal', { ...comparison, transfers: 'excluded' }, all)).toBe(all[5]);
	});

	it('has nothing for all provinces counted as their governments alone', () => {
		const alone = { ...comparison, provinceView: 'provincial_government' } as Comparison;
		expect(seriesFor(ALL_PROVINCES, alone, all)).toBeUndefined();
	});

	it('has nothing when the data has no such series', () => {
		expect(seriesFor('qc', comparison, all)).toBeUndefined();
	});
});

describe('compareFileFor', () => {
	const parentOf = (id: string) => (id.length === 4 ? id.slice(0, 3) : null);

	it('finds the file holding total spending, a function or a sub-function', () => {
		expect(compareFileFor(TOTAL, parentOf)).toBe(TOTAL);
		expect(compareFileFor('707', parentOf)).toBe('707');
		expect(compareFileFor('7073', parentOf)).toBe('707');
	});
});
