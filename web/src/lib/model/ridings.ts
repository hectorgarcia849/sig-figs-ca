/**
 * The ridings page's data and choices, kept apart from the page so they can be tested:
 *
 *   - each riding's summary (current name, winner, margin, turnout), built into the page
 *   - seat counts per party, and each party's colour on the map
 *   - finding ridings by name, ignoring accents, dashes and capitals
 *   - the choices in the address: the selected riding, the party and province filters
 */
import type { Language } from '#lib/i18n/index.ts';
import type {
	Election,
	ElectionCandidate,
	ElectionDistrict,
	Party,
	Riding
} from '#lib/model/types.ts';

/** One riding, as the page shows it: its names, winner and turnout at one election. */
export interface RidingSummary {
	code: string;
	name_en: string;
	name_fr: string;
	jurisdiction: string;
	/** The riding's name on election day, only when it has been renamed since. */
	nameAtElection: { en: string; fr: string } | null;
	winner: string;
	party: string;
	incumbent: boolean;
	share: number; // the winner's share of the vote, in percent
	marginVotes: number;
	marginPct: number;
	turnout: number; // in percent
}

/** One candidate's result, as /data/ridings/candidates.json gives it. */
export interface CandidateResult {
	election: string;
	riding: string;
	candidate: string;
	party: string;
	votes: number;
	share: number;
	elected: boolean;
	incumbent: boolean;
}

/** The election the page shows: the most recent general election. */
export function latestGeneralElection(elections: Election[]): Election {
	const general = elections.filter((each) => each.general);
	if (general.length === 0) throw new Error('No general election in elections.json');
	return general.reduce((latest, each) => (each.voting_day > latest.voting_day ? each : latest));
}

/** Every riding's summary at one election, in riding-number order. */
export function ridingSummaries(
	ridings: Riding[],
	districts: ElectionDistrict[],
	candidates: ElectionCandidate[],
	election: string
): RidingSummary[] {
	const districtOf = new Map(
		districts.filter((each) => each.election === election).map((each) => [each.riding, each])
	);
	const winnerOf = new Map(
		candidates
			.filter((each) => each.election === election && each.elected)
			.map((each) => [each.riding, each])
	);
	return ridings.map((riding) => {
		const district = districtOf.get(riding.code);
		const winner = winnerOf.get(riding.code);
		if (!district || !winner) throw new Error(`No ${election} result for riding ${riding.code}`);
		return {
			code: riding.code,
			name_en: riding.name_en,
			name_fr: riding.name_fr,
			jurisdiction: riding.jurisdiction,
			nameAtElection: district.renamed
				? { en: district.name_at_election_en, fr: district.name_at_election_fr }
				: null,
			winner: winner.candidate,
			party: winner.party,
			incumbent: winner.incumbent,
			share: winner.vote_share_pct,
			marginVotes: winner.margin_votes ?? 0,
			marginPct: winner.margin_pct ?? 0,
			turnout: district.turnout_pct
		};
	});
}

/** Seats won by each party that won any, most first (ties in the parties' own order). */
export function seatCounts(
	summaries: RidingSummary[],
	parties: Party[]
): { party: Party; seats: number }[] {
	const seats = new Map<string, number>();
	for (const summary of summaries) seats.set(summary.party, (seats.get(summary.party) ?? 0) + 1);
	return parties
		.filter((party) => seats.has(party.code))
		.map((party) => ({ party, seats: seats.get(party.code)! }))
		.sort((a, b) => b.seats - a.seats || a.party.sort_order - b.party.sort_order);
}

// --- Colours ------------------------------------------------------------------

/**
 * Each party's own colour, the convention readers expect on election maps.
 * Parties without one here are grey. Colour is never the only clue: the legend,
 * labels and table name the party too.
 */
export const PARTY_COLOURS: Record<string, string> = {
	liberal: '#d71920',
	conservative: '#1a4782',
	bloc: '#33b2cc',
	ndp: '#f58220',
	green: '#3d9b35',
	ppc: '#4e2a84'
};
export const OTHER_PARTY_COLOUR = '#8c8c8c';

export function partyColour(code: string): string {
	return PARTY_COLOURS[code] ?? OTHER_PARTY_COLOUR;
}

/** A party's short name in one language, e.g. "NDP" or "NPD". */
export function partyShortName(party: Party | undefined, code: string, lang: Language): string {
	if (!party) return code;
	return lang === 'en' ? party.short_en : party.short_fr;
}

// --- Finding ridings by name ----------------------------------------------------

/**
 * Text ready to compare: lower case, without accents, with dashes, apostrophes
 * and other punctuation as spaces. "Côte-Nord—Kawawachikamach" and "cote nord
 * kawawachikamach" match.
 */
export function searchKey(text: string): string {
	return text
		.normalize('NFD')
		.replace(/\p{Diacritic}/gu, '')
		.toLowerCase()
		.replace(/[^\p{Letter}\p{Number}]+/gu, ' ')
		.trim();
}

/**
 * Ridings whose name (English, French, or on election day) contains the search,
 * ridings starting with it first, then in name order. At most `limit` of them.
 */
export function searchRidings(
	summaries: RidingSummary[],
	search: string,
	lang: Language,
	limit = 8
): RidingSummary[] {
	const wanted = searchKey(search);
	if (wanted === '') return [];
	const names = (summary: RidingSummary) =>
		[
			summary.name_en,
			summary.name_fr,
			summary.nameAtElection?.en ?? '',
			summary.nameAtElection?.fr ?? ''
		].map(searchKey);
	const ranked = summaries.flatMap((summary) => {
		const keys = names(summary);
		if (!keys.some((key) => key.includes(wanted))) return [];
		const startsWith = keys.some((key) => key.startsWith(wanted) || key.includes(` ${wanted}`));
		return [{ summary, rank: startsWith ? 0 : 1 }];
	});
	const name = (summary: RidingSummary) => (lang === 'en' ? summary.name_en : summary.name_fr);
	return ranked
		.sort((a, b) => a.rank - b.rank || name(a.summary).localeCompare(name(b.summary), lang))
		.slice(0, limit)
		.map((each) => each.summary);
}

// --- The choices, kept in the address ---------------------------------------------

/** What the visitor has chosen: a riding to look at, and which parties and province to show. */
export interface RidingView {
	riding: string | null;
	parties: string[]; // empty: every party
	province: string | null; // null: all of Canada
}

export const DEFAULT_VIEW: RidingView = { riding: null, parties: [], province: null };

// The address's query parameters: /en/ridings?riding=35105&party=ndp,green&province=on
const PARAMETERS = { riding: 'riding', parties: 'party', province: 'province' } as const;

/** The choices in an address's query, keeping only real ridings, parties and provinces. */
export function readRidingView(
	search: URLSearchParams,
	allowed: { ridings: string[]; parties: string[]; provinces: string[] }
): RidingView {
	const riding = search.get(PARAMETERS.riding);
	const province = search.get(PARAMETERS.province);
	const parties = (search.get(PARAMETERS.parties) ?? '')
		.split(',')
		.filter((code) => allowed.parties.includes(code));
	return {
		riding: riding && allowed.ridings.includes(riding) ? riding : null,
		parties: [...new Set(parties)],
		province: province && allowed.provinces.includes(province) ? province : null
	};
}

/** The query for some choices, without the "?"; empty for the default view. */
export function ridingViewQuery(view: RidingView): string {
	const query = new URLSearchParams();
	if (view.riding) query.set(PARAMETERS.riding, view.riding);
	if (view.parties.length > 0) query.set(PARAMETERS.parties, view.parties.join(','));
	if (view.province) query.set(PARAMETERS.province, view.province);
	// Commas are safe in a query and easier to read than %2C.
	return query.toString().replaceAll('%2C', ',');
}

/** Whether a riding passes the party and province filters. */
export function passesFilters(summary: RidingSummary, view: RidingView): boolean {
	return (
		(view.parties.length === 0 || view.parties.includes(summary.party)) &&
		(view.province === null || summary.jurisdiction === view.province)
	);
}
