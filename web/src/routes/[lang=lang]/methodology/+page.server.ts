// Methodology and sources: every Statistics Canada table behind the figures.
import { readMeta } from '#lib/server/data.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => ({ sources: readMeta().sources });
