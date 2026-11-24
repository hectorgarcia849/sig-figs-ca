// /data/ridings/map.json: the ridings' shapes (TopoJSON), loaded by the
// ridings page once it opens. Built once, with the site.
import { json } from '@sveltejs/kit';
import { readRidingMap } from '#lib/server/data.ts';
import type { RequestHandler } from './$types';

export const prerender = true;

export const GET: RequestHandler = () => json(readRidingMap());
