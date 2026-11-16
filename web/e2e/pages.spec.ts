/**
 * Every page in the sitemap: it loads, has no errors (a blocked script shows
 * up as one), has no serious accessibility problems, and links to the same
 * page in the other language.
 */
import { expect, test } from '@playwright/test';
import { blockingAccessibilityProblems, recordErrors, sitemapAddresses } from './helpers.ts';

const LANGUAGES = ['en', 'fr'];
const LOCALES: Record<string, string> = { en: 'en-CA', fr: 'fr-CA' };
const ADDRESSES = sitemapAddresses();

test('the sitemap lists the welcome page and every page in both languages', () => {
	expect(ADDRESSES).toContain('/');
	for (const address of ADDRESSES.filter((each) => each.startsWith('/en'))) {
		expect(ADDRESSES).toContain(address.replace(/^\/en/, '/fr'));
	}
	expect(ADDRESSES.length).toBeGreaterThan(50);
});

for (const address of ADDRESSES) {
	test(`${address}`, async ({ page }) => {
		const errors = recordErrors(page);
		const response = await page.goto(address, { waitUntil: 'networkidle' });
		expect(response?.status()).toBe(200);

		expect(await blockingAccessibilityProblems(page)).toEqual([]);
		await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
			'href',
			new RegExp(`${address === '/' ? '/' : address}$`)
		);

		const lang = address.split('/')[1];
		if (LANGUAGES.includes(lang)) {
			const other = lang === 'en' ? 'fr' : 'en';
			const otherAddress = address.replace(`/${lang}`, `/${other}`);
			await expect(page.locator('html')).toHaveAttribute('lang', lang);
			await expect(page.locator(`header a[hreflang="${other}"]`)).toHaveAttribute(
				'href',
				otherAddress
			);
			await expect(
				page.locator(`link[rel="alternate"][hreflang="${LOCALES[other]}"]`)
			).toHaveAttribute('href', new RegExp(`${otherAddress}$`));
		}

		expect(errors).toEqual([]);
	});
}
