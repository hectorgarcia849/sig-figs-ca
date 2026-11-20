/**
 * Which version of the code the site was built from: the git commit, with
 * "-dirty" added when the folder had changes not yet committed. Null when git
 * cannot say (e.g. a copy of the code made without git).
 *
 * Shown in /build.json, next to the data build, so anyone can tell which code
 * and which data the live site shows.
 */
import { execFileSync } from 'node:child_process';

// Added to the commit when the code had changes not yet committed.
const UNCOMMITTED_MARK = '-dirty';

function git(...args: string[]): string {
	return execFileSync('git', args, {
		encoding: 'utf-8',
		stdio: ['ignore', 'pipe', 'ignore']
	}).trim();
}

export function codeCommit(): string | null {
	try {
		const commit = git('rev-parse', 'HEAD');
		const changed = git('status', '--porcelain', '--untracked-files=no') !== '';
		return changed ? commit + UNCOMMITTED_MARK : commit;
	} catch {
		return null;
	}
}
