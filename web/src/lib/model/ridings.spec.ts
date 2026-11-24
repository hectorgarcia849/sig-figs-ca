import { describe, expect, it } from 'vitest';
import {
	DEFAULT_VIEW,
	OTHER_PARTY_COLOUR,
	latestGeneralElection,
	partyColour,
	passesFilters,
	readRidingView,
	ridingSummaries,
	ridingViewQuery,
	searchKey,
	searchRidings,
	seatCounts,
	type RidingSummary
} from './ridings.ts';
import type { ElectionCandidate, ElectionDistrict, Party, Riding } from './types.ts';

const RIDINGS: Riding[] = [
	{ code: '10001', name_en: 'Avalon', name_fr: 'Avalon', jurisdiction: 'nl' },
	{ code: '35120', name_en: 'North York', name_fr: 'North York', jurisdiction: 'on' },
	{
		code: '24021',
		name_en: 'Côte-Nord—Kawawachikamach—Nitassinan',
		name_fr: 'Côte-Nord—Kawawachikamach—Nitassinan',
		jurisdiction: 'qc'
	}
];

const district = (riding: string, renamed = false, name = ''): ElectionDistrict => ({
	election: 'ge45',
	riding,
	name_at_election_en: name,
	name_at_election_fr: name,
	renamed,
	electors: 70000,
	valid_ballots: 47030,
	rejected_ballots: 389,
	total_ballots: 47419,
	turnout_pct: 66.9,
	release: '2026-11-24',
	source_id: 'elections-ge45_results_by_district'
});

const candidate = (
	riding: string,
	name: string,
	party: string,
	elected: boolean,
	incumbent = false
): ElectionCandidate => ({
	election: 'ge45',
	riding,
	candidate: name,
	party,
	votes: elected ? 27563 : 16953,
	vote_share_pct: elected ? 58.6 : 36.0,
	elected,
	incumbent,
	margin_votes: elected ? 10610 : null,
	margin_pct: elected ? 22.6 : null,
	release: '2026-11-24',
	source_id: 'elections-ge45_results_by_candidate'
});

const PARTIES: Party[] = [
	{ code: 'liberal', name_en: 'Liberal', name_fr: 'Libéral', short_en: 'Liberal', short_fr: 'Libéral', sort_order: 1 },
	{ code: 'conservative', name_en: 'Conservative', name_fr: 'Conservateur', short_en: 'Conservative', short_fr: 'Conservateur', sort_order: 2 },
	{ code: 'bloc', name_en: 'Bloc Québécois', name_fr: 'Bloc Québécois', short_en: 'Bloc', short_fr: 'Bloc', sort_order: 3 }
]; // prettier-ignore

const SUMMARIES = ridingSummaries(
	RIDINGS,
	[district('10001'), district('35120', true, 'York Centre'), district('24021')],
	[
		candidate('10001', 'Paul Connors', 'liberal', true),
		candidate('10001', 'Steve Kent', 'conservative', false),
		candidate('35120', 'Roman Baber', 'conservative', true),
		candidate('24021', 'Someone', 'bloc', true, true)
	],
	'ge45'
);

describe('riding summaries', () => {
	it('give each riding its winner, margin and turnout', () => {
		expect(SUMMARIES[0]).toEqual({
			code: '10001',
			name_en: 'Avalon',
			name_fr: 'Avalon',
			jurisdiction: 'nl',
			nameAtElection: null,
			winner: 'Paul Connors',
			party: 'liberal',
			incumbent: false,
			share: 58.6,
			marginVotes: 10610,
			marginPct: 22.6,
			turnout: 66.9
		});
	});

	it("keep a renamed riding's name on election day", () => {
		expect(SUMMARIES[1].nameAtElection).toEqual({ en: 'York Centre', fr: 'York Centre' });
	});

	it('stop the build when a riding has no result', () => {
		expect(() => ridingSummaries(RIDINGS, [district('10001')], [], 'ge45')).toThrow(
			'No ge45 result for riding 10001'
		);
	});
});

describe('the latest general election', () => {
	it('is the newest general election, not a later by-election', () => {
		const election = latestGeneralElection([
			{ code: 'ge44', name_en: '', name_fr: '', voting_day: '2021-09-20', general: true },
			{ code: 'ge45', name_en: '', name_fr: '', voting_day: '2025-04-28', general: true },
			{ code: 'by-2025-08', name_en: '', name_fr: '', voting_day: '2025-08-18', general: false }
		]);
		expect(election.code).toBe('ge45');
	});
});

describe('seat counts', () => {
	it('list parties that won seats, most first', () => {
		const counts = seatCounts(SUMMARIES, PARTIES).map(({ party, seats }) => [party.code, seats]);
		expect(counts).toEqual([
			['liberal', 1],
			['conservative', 1],
			['bloc', 1]
		]);
	});
});

describe('party colours', () => {
	it('use the party colour, or grey for parties without one', () => {
		expect(partyColour('ndp')).toBe('#f58220');
		expect(partyColour('rhinoceros')).toBe(OTHER_PARTY_COLOUR);
	});
});

describe('finding ridings by name', () => {
	it('ignores accents, dashes and capitals', () => {
		expect(searchKey('Côte-Nord—Kawawachikamach')).toBe('cote nord kawawachikamach');
		expect(searchRidings(SUMMARIES, 'cote nord', 'en').map((each) => each.code)).toEqual(['24021']);
	});

	it('finds a renamed riding by its old name', () => {
		expect(searchRidings(SUMMARIES, 'york centre', 'en').map((each) => each.code)).toEqual([
			'35120'
		]);
	});

	it('lists names with a word starting with the search first', () => {
		const ridings: RidingSummary[] = [
			{ ...SUMMARIES[0], code: '1', name_en: 'North Okanagan', name_fr: 'North Okanagan' },
			{ ...SUMMARIES[0], code: '2', name_en: 'Northwest Territories', name_fr: 'Territoires' },
			{ ...SUMMARIES[0], code: '3', name_en: 'Abnorthville', name_fr: 'Abnorthville' }
		];
		expect(searchRidings(ridings, 'north', 'en').map((each) => each.code)).toEqual(['1', '2', '3']);
	});

	it('finds nothing for an empty search', () => {
		expect(searchRidings(SUMMARIES, '  ', 'en')).toEqual([]);
	});
});

describe('the choices in the address', () => {
	const allowed = {
		ridings: ['10001', '35120'],
		parties: ['liberal', 'ndp'],
		provinces: ['nl', 'on']
	};

	it('round-trip through the query', () => {
		const view = { riding: '35120', parties: ['ndp', 'liberal'], province: 'on' };
		const query = ridingViewQuery(view);
		expect(query).toBe('riding=35120&party=ndp,liberal&province=on');
		expect(readRidingView(new URLSearchParams(query), allowed)).toEqual(view);
	});

	it('leave the default view with no query', () => {
		expect(ridingViewQuery(DEFAULT_VIEW)).toBe('');
		expect(readRidingView(new URLSearchParams(''), allowed)).toEqual(DEFAULT_VIEW);
	});

	it('drop anything that is not a real riding, party or province', () => {
		const search = new URLSearchParams('riding=99999&party=ndp,nobody,ndp&province=zz');
		expect(readRidingView(search, allowed)).toEqual({
			riding: null,
			parties: ['ndp'],
			province: null
		});
	});

	it('filter ridings by party and province', () => {
		expect(passesFilters(SUMMARIES[0], { ...DEFAULT_VIEW, parties: ['liberal'] })).toBe(true);
		expect(passesFilters(SUMMARIES[0], { ...DEFAULT_VIEW, parties: ['bloc'] })).toBe(false);
		expect(passesFilters(SUMMARIES[0], { ...DEFAULT_VIEW, province: 'on' })).toBe(false);
	});
});
