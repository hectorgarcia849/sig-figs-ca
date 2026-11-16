import { describe, expect, it } from 'vitest';
import { addressInOtherLanguage, isLanguage, otherLanguage } from './index.ts';

describe('languages', () => {
	it('accepts only en and fr', () => {
		expect(isLanguage('en')).toBe(true);
		expect(isLanguage('fr')).toBe(true);
		expect(isLanguage('de')).toBe(false);
		expect(isLanguage('english')).toBe(false);
	});

	it('switches to the other language', () => {
		expect(otherLanguage('en')).toBe('fr');
		expect(otherLanguage('fr')).toBe('en');
	});

	it('gives the same address in the other language', () => {
		expect(addressInOtherLanguage('/en/governments/on', 'en')).toBe('/fr/governments/on');
		expect(addressInOtherLanguage('/fr', 'fr')).toBe('/en');
		// Only the language at the start changes.
		expect(addressInOtherLanguage('/en/functions/en', 'en')).toBe('/fr/functions/en');
	});
});
