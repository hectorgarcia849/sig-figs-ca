// /data/ridings/candidates.json: every candidate's result, loaded by the
// ridings page once it opens (each riding's winner is built into the page).
// Only the columns the page shows. Built once, with the site.
import { json } from '@sveltejs/kit';
import { readElectionCandidates } from '#lib/server/data.ts';
import type { CandidateResult } from '#lib/model/ridings.ts';
import type { RequestHandler } from './$types';

export const prerender = true;

export const GET: RequestHandler = () =>
	json(
		readElectionCandidates().map((row): CandidateResult => ({
			election: row.election,
			riding: row.riding,
			candidate: row.candidate,
			party: row.party,
			votes: row.votes,
			share: row.vote_share_pct,
			elected: row.elected,
			incumbent: row.incumbent
		}))
	);
