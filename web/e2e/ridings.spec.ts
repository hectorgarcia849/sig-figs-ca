/**
 * The ridings page: the map loads, a riding can be chosen from the map, the
 * search or the table, the filters and the chosen riding are kept in the
 * address, and the results match Elections Canada's for a few ridings.
 * (Errors and accessibility on its default view are checked with every page.)
 */
import { expect, test, type Page } from '@playwright/test';
import { blockingAccessibilityProblems, recordErrors } from './helpers.ts';

const map = (page: Page) => page.getByRole('application', { name: 'Map of the ridings' });
const riding = (page: Page, code: string) => page.locator(`path[data-code="${code}"]`);
const panelHeading = (page: Page) => page.locator('#riding-name');
const tableCount = (page: Page) => page.getByText(/ of 343 ridings shown\.$/);

async function openPage(page: Page, query = '') {
	await page.goto(`/en/ridings${query}`, { waitUntil: 'networkidle' });
	await expect(riding(page, '10001')).toBeAttached();
}

test('shows every party that won seats, and the map of all 343 ridings', async ({ page }) => {
	const errors = recordErrors(page);
	await openPage(page);
	for (const label of ['Liberal: 169', 'Conservative: 144', 'Bloc: 22', 'NDP: 7', 'Green: 1']) {
		await expect(page.getByRole('button', { name: label })).toBeVisible();
	}
	await expect(page.locator('path[data-code]')).toHaveCount(343);
	await expect(tableCount(page)).toHaveText('343 of 343 ridings shown.');
	expect(errors).toEqual([]);
});

test('clicking a riding on the map shows its result and puts it in the address', async ({
	page
}) => {
	await openPage(page);
	// A compact riding: a click at the middle of its box lands on it, not on water.
	await riding(page, '47012').click();
	await expect(panelHeading(page)).toHaveText('Souris—Moose Mountain');
	await expect(page).toHaveURL(/\?riding=47012$/);
	await page.getByRole('button', { name: 'Close' }).click();
	await expect(page).toHaveURL(/\/en\/ridings$/);
});

test('a riding can be found by its name on election day', async ({ page }) => {
	await openPage(page);
	await page.getByLabel('Find a riding').fill('york centre');
	await page.getByRole('button', { name: 'North York', exact: true }).click();
	await expect(panelHeading(page)).toHaveText('North York');
	await expect(page.getByText('Called York Centre at the 2025 election.')).toBeVisible();
	// Every candidate, loaded after the page opened.
	await expect(page.getByRole('rowheader', { name: "Ya'ara Saks" })).toBeVisible();
});

test('party and province filters narrow the table and are kept in the address', async ({
	page
}) => {
	await openPage(page);
	await page.getByRole('button', { name: 'NDP: 7' }).click();
	await expect(page.getByRole('button', { name: 'NDP: 7' })).toHaveAttribute(
		'aria-pressed',
		'true'
	);
	await expect(tableCount(page)).toHaveText('7 of 343 ridings shown.');
	await page.getByLabel('Province or territory').selectOption('bc');
	await expect(page).toHaveURL(/\?party=ndp&province=bc$/);
	await page.getByRole('button', { name: 'Show all parties' }).click();
	await expect(tableCount(page)).toHaveText('43 of 343 ridings shown.');
});

test('opening a shared address restores the riding and filters', async ({ page }) => {
	await openPage(page, '?riding=35120&party=conservative&province=on');
	await expect(panelHeading(page)).toHaveText('North York');
	await expect(page.getByRole('button', { name: 'Conservative: 144' })).toHaveAttribute(
		'aria-pressed',
		'true'
	);
	await expect(page.getByLabel('Province or territory')).toHaveValue('on');
	expect(await blockingAccessibilityProblems(page)).toEqual([]);
});

test('the language switch keeps the chosen riding', async ({ page }) => {
	await openPage(page, '?riding=10001');
	await page.getByRole('link', { name: 'Français' }).click();
	await expect(page).toHaveURL(/\/fr\/ridings\?riding=10001$/);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Circonscriptions fédérales');
	await expect(panelHeading(page)).toHaveText('Avalon');
});

test('the map moves and zooms by keyboard', async ({ page }) => {
	await openPage(page);
	const shapes = map(page).locator('g').first();
	await map(page).focus();
	await page.keyboard.press('+');
	await expect(shapes).not.toHaveAttribute('transform', 'translate(0,0) scale(1)');
	await page.getByRole('button', { name: 'Show all of Canada' }).click();
	await expect(shapes).toHaveAttribute('transform', 'translate(0,0) scale(1)');
});

test('choosing a riding in the table shows it on the map', async ({ page }) => {
	await openPage(page);
	await page.getByRole('button', { name: 'Show Carleton on the map' }).click();
	await expect(panelHeading(page)).toHaveText('Carleton');
	await expect(page).toHaveURL(/\?riding=35020$/);
});

// Checked against Elections Canada's official results for the 45th general election.
const OFFICIAL_RESULTS = [
	{ riding: 'Avalon', winner: 'Paul Connors', party: 'Liberal', margin: '10,610' },
	{ riding: 'Carleton', winner: 'Bruce Fanjoy', party: 'Liberal', margin: '4,513' },
	{ riding: 'Terrebonne', winner: 'Tatiana Auguste', party: 'Liberal', margin: '1' },
	{ riding: 'Nunavut', winner: 'Lori Idlout', party: 'NDP', margin: '41' },
	{ riding: 'North York', winner: 'Roman Baber', party: 'Conservative', margin: '5,792' }
];

for (const result of OFFICIAL_RESULTS) {
	test(`the table gives ${result.riding}'s official result`, async ({ page }) => {
		await openPage(page);
		const row = page.getByRole('row').filter({
			has: page.getByRole('button', { name: `Show ${result.riding} on the map`, exact: true })
		});
		await expect(row.getByRole('cell').nth(1)).toHaveText(result.winner);
		await expect(row.getByRole('cell').nth(2)).toHaveText(result.party);
		await expect(row.getByRole('cell').nth(4)).toHaveText(result.margin);
	});
}
