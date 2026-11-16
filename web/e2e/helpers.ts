/** Shared pieces for the page checks. */
import { readFileSync } from 'node:fs';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';

// Accessibility problems that fail a check. axe also reports "minor" and
// "moderate" ones, which are worth reading but do not block a release.
const BLOCKING_IMPACTS = ['serious', 'critical'];

/** Every page of the built site, as an address like /en/governments/on, from its sitemap. */
export function sitemapAddresses(): string[] {
	const sitemap = readFileSync('build/sitemap.xml', 'utf-8');
	return [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => new URL(match[1]).pathname);
}

/** Starts recording the page's console errors and uncaught errors (including blocked scripts). */
export function recordErrors(page: Page): string[] {
	const errors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') errors.push(message.text());
	});
	page.on('pageerror', (error) => errors.push(error.message));
	return errors;
}

/** The serious and critical accessibility problems axe finds on the page, one line each. */
export async function blockingAccessibilityProblems(page: Page): Promise<string[]> {
	const results = await new AxeBuilder({ page }).analyze();
	return results.violations
		.filter((violation) => BLOCKING_IMPACTS.includes(violation.impact ?? ''))
		.map((violation) => `${violation.id}: ${violation.help} (${violation.nodes.length} places)`);
}
