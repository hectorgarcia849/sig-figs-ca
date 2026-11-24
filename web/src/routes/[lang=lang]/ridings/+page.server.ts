// The ridings page: each riding's result at the latest general election, built
// into the page. The map's shapes and every candidate's result are loaded by
// the page once it opens (/data/ridings/map.json and candidates.json).
import {
	readElectionCandidates,
	readElectionDistricts,
	readElections,
	readParties,
	readRidings
} from '#lib/server/data.ts';
import { latestGeneralElection, ridingSummaries } from '#lib/model/ridings.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => {
	const election = latestGeneralElection(readElections());
	return {
		election,
		parties: readParties(),
		summaries: ridingSummaries(
			readRidings(),
			readElectionDistricts(),
			readElectionCandidates(),
			election.code
		)
	};
};
