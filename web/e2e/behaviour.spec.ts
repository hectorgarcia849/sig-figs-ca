/**
 * How the site behaves: keyboard use, phone-width layout, chart descriptions,
 * CSV downloads, the "page not found" page and the build record.
 */
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { blockingAccessibilityProblems, recordErrors } from './helpers.ts';

const PHONE = { width: 375, height: 812 };
const PHONE_PAGES = [
	'/',
	'/en',
	'/en/ridings?riding=35120',
	'/fr/governments/federal',
	'/en/governments/on',
	'/en/functions/707',
	'/en/methodology'
];

test('the skip link is the first thing a keyboard reaches and jumps to the content', async ({
	page
}) => {
	await page.goto('/en');
	await page.keyboard.press('Tab');
	await expect(page.locator(':focus')).toHaveText('Skip to main content');
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/#main$/);
	await page.keyboard.press('Tab');
	expect(await page.locator(':focus').evaluate((element) => !!element.closest('main'))).toBe(true);
});

test('the transfers switch works by keyboard and changes the figures', async ({ page }) => {
	await page.goto('/en/governments/federal', { waitUntil: 'networkidle' });
	const total = page.locator('.figure .value').first();
	const before = await total.textContent();

	await page.getByRole('radio', { name: 'Including transfers' }).focus();
	await page.keyboard.press('ArrowDown');
	await expect(page.getByRole('radio', { name: 'Excluding transfers' })).toBeChecked();
	await expect(total).not.toHaveText(before ?? '');
});

for (const address of PHONE_PAGES) {
	test(`${address} fits a phone screen without scrolling sideways`, async ({ page }) => {
		await page.setViewportSize(PHONE);
		await page.goto(address, { waitUntil: 'networkidle' });
		const overflow = await page.evaluate(
			() => document.documentElement.scrollWidth - document.documentElement.clientWidth
		);
		expect(overflow).toBeLessThanOrEqual(0);
	});
}

test('every chart has a text description', async ({ page }) => {
	await page.goto('/en', { waitUntil: 'networkidle' });
	const charts = page.locator('[role="img"]');
	expect(await charts.count()).toBeGreaterThan(0);
	for (const label of await charts.evaluateAll((all) => all.map((chart) => chart.ariaLabel))) {
		expect(label?.trim()).toBeTruthy();
	}
});

test('CSV downloads work with the security policy in place', async ({ page }) => {
	const errors = recordErrors(page);
	await page.goto('/en', { waitUntil: 'networkidle' });
	const download = page.waitForEvent('download');
	await page.getByRole('button', { name: 'Download CSV' }).first().click();
	expect((await download).suggestedFilename()).toMatch(/\.csv$/);
	expect(errors).toEqual([]);
});

test('the page-not-found page is in both languages, with no script', async ({ page }) => {
	const errors = recordErrors(page);
	await page.goto('/404');
	await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Page introuvable' })).toBeVisible();
	await expect(page.locator('script')).toHaveCount(0);
	await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex');
	expect(await blockingAccessibilityProblems(page)).toEqual([]);
	expect(errors).toEqual([]);
});

test('build.json names the build the site was made from', async ({ request }) => {
	const exported = JSON.parse(readFileSync('data/meta.json', 'utf-8'));
	const published = await (await request.get('/build.json')).json();
	expect(published.build_id).toBe(exported.build_id);
	expect(published.commit).toMatch(/^[0-9a-f]{40}(-dirty)?$/);
});
