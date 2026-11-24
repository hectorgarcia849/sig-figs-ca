/**
 * Reads the files "pst export" wrote to web/data/.
 *
 * Only runs while the site is being built (or in the local dev server): files
 * under lib/server never reach the browser. Each page's load function picks
 * the rows it needs from here, and only those rows are built into the page.
 *
 * Each file is read once and kept in memory for the rest of the build.
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type {
	Election,
	ElectionCandidate,
	ElectionDistrict,
	GovernmentFunction,
	Jurisdiction,
	Meta,
	MunicipalTransferRow,
	Party,
	Riding,
	SpendingRow
} from '#lib/model/types.ts';

// web/data. Paths are relative to the web folder, where every site command runs.
const DATA_FOLDER = path.resolve('data');

const alreadyRead = new Map<string, unknown>();

function readJson<T>(fileName: string): T {
	if (!alreadyRead.has(fileName)) {
		const file = path.join(DATA_FOLDER, fileName);
		if (!existsSync(file)) {
			throw new Error(
				`${file} is missing. Run "uv run pst export" from the repository root first.`
			);
		}
		alreadyRead.set(fileName, JSON.parse(readFileSync(file, 'utf-8')));
	}
	return alreadyRead.get(fileName) as T;
}

export const readMeta = () => readJson<Meta>('meta.json');
export const readJurisdictions = () => readJson<Jurisdiction[]>('jurisdictions.json');
export const readFunctions = () => readJson<GovernmentFunction[]>('functions.json');
export const readSpending = () => readJson<SpendingRow[]>('spending.json');
export const readMunicipalTransfers = () =>
	readJson<MunicipalTransferRow[]>('municipal_transfers.json');

// The riding map's files.
export const readElections = () => readJson<Election[]>('elections.json');
export const readParties = () => readJson<Party[]>('parties.json');
export const readRidings = () => readJson<Riding[]>('ridings.json');
export const readElectionDistricts = () => readJson<ElectionDistrict[]>('election_districts.json');
export const readElectionCandidates = () =>
	readJson<ElectionCandidate[]>('election_candidates.json');
/** The ridings' shapes, as TopoJSON. Passed on to the browser as it is. */
export const readRidingMap = () => readJson<unknown>('ridings.topo.json');

/** The IDs of the 10 functions ("701" to "710"), in order. */
export function functionIds(): string[] {
	return readFunctions()
		.filter((each) => each.level === 1)
		.map((each) => each.function_id);
}

/** The IDs of one function's sub-functions. */
export function subFunctionIds(functionId: string): string[] {
	return readFunctions()
		.filter((each) => each.parent_id === functionId)
		.map((each) => each.function_id);
}
