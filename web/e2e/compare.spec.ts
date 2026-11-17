/**
 * The Compare page: choices kept in the address, loading other spending,
 * the 7-government limit, the language switch and the links into Compare.
 * (Errors and accessibility on its default view are checked with every page.)
 */
import { expect, test, type Page } from '@playwright/test';
import { blockingAccessibilityProblems, recordErrors } from './helpers.ts';

const governmentBox = (page: Page, name: string) =>
	page.getByRole('checkbox', { name, exact: true });
const spendingList = (page: Page) => page.getByLabel('Spending on');

test('starts with total spending per person in the four largest provinces', async ({ page }) => {
	const errors = recordErrors(page);
	await page.goto('/en/compare', { waitUntil: 'networkidle' });
	for (const name of ['Ontario', 'Quebec', 'British Columbia', 'Alberta']) {
		await expect(governmentBox(page, name)).toBeChecked();
	}
	await expect(page).toHaveURL(
		/\?gov=on,qc,bc,ab&spending=total&measure=amount_per_person&year=\d+$/
	);
	await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText(
		/^Total spending per person, 2008-09 to \d{4}-\d{2}$/
	);
	expect(errors).toEqual([]);
});

test('changing a choice updates the charts and the address', async ({ page }) => {
	const errors = recordErrors(page);
	await page.goto('/en/compare', { waitUntil: 'networkidle' });
	await governmentBox(page, 'Manitoba').check();
	await expect(page).toHaveURL(/gov=on,qc,bc,ab,mb&/);
	await spendingList(page).selectOption('707');
	await expect(page).toHaveURL(/spending=707&/);
	await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText(/^Health per person/);
	const rankingRows = page
		.locator('table', { has: page.locator('caption', { hasText: ': highest in' }) })
		.locator('tbody tr');
	await expect(rankingRows).toHaveCount(5);
	expect(await blockingAccessibilityProblems(page)).toEqual([]);
	expect(errors).toEqual([]);
});

test('opening a shared address restores its comparison', async ({ page }) => {
	await page.goto(
		'/en/compare?gov=nu,federal&spending=7073&measure=amount&year=2020&transfers=included',
		{ waitUntil: 'networkidle' }
	);
	await expect(governmentBox(page, 'Nunavut')).toBeChecked();
	await expect(governmentBox(page, 'Federal government')).toBeChecked();
	await expect(governmentBox(page, 'Ontario')).not.toBeChecked();
	await expect(spendingList(page)).toHaveValue('7073');
	await expect(page.getByRole('radio', { name: 'Dollars', exact: true })).toBeChecked();
	await expect(page.getByLabel('Year')).toHaveValue('2020');
});

test('at most 7 governments can be chosen at once', async ({ page }) => {
	await page.goto('/en/compare?gov=nl,pe,ns,nb,qc,on,mb', { waitUntil: 'networkidle' });
	await expect(governmentBox(page, 'Saskatchewan')).toBeDisabled();
	await expect(page.getByText('Up to 7 at once')).toBeVisible();
	await governmentBox(page, 'Manitoba').uncheck();
	await expect(governmentBox(page, 'Saskatchewan')).toBeEnabled();
});

test('governments with no figures for the choices are named', async ({ page }) => {
	await page.goto('/en/compare?gov=on,all-provinces&view=provincial_government', {
		waitUntil: 'networkidle'
	});
	await expect(page.getByRole('status').last()).toHaveText(
		'No figures with these choices for: All provinces and territories.'
	);
});

test('the language switch keeps the comparison', async ({ page }) => {
	await page.goto('/en/compare?gov=nu,on&spending=707', { waitUntil: 'networkidle' });
	await page.getByRole('link', { name: 'Français' }).click();
	await expect(page).toHaveURL(/\/fr\/compare\?gov=nu,on&spending=707&/);
	await expect(governmentBox(page, 'Nunavut')).toBeChecked();
	await expect(page.getByLabel('Dépenses examinées')).toHaveValue('707');
});

test('function and province pages link into Compare', async ({ page }) => {
	await page.goto('/en/functions/707', { waitUntil: 'networkidle' });
	await page.getByRole('link', { name: 'Compare governments on this function' }).click();
	await expect(spendingList(page)).toHaveValue('707');

	await page.goto('/en/governments/nu', { waitUntil: 'networkidle' });
	await page.getByRole('link', { name: 'Compare with other provinces and territories' }).click();
	await expect(governmentBox(page, 'Nunavut')).toBeChecked();
	await expect(page).toHaveURL(/gov=nu,on,qc,bc&/);
});

test('the link to the comparison can be copied', async ({ page, context }) => {
	await context.grantPermissions(['clipboard-read', 'clipboard-write']);
	await page.goto('/en/compare?gov=nu,on', { waitUntil: 'networkidle' });
	await page.getByRole('button', { name: 'Copy link to this comparison' }).click();
	await expect(page.getByText('Link copied.')).toBeVisible();
	expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
		'/en/compare?gov=nu,on&'
	);
});
