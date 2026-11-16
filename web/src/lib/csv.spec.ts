import { describe, expect, it } from 'vitest';
import { toCsv } from './csv.ts';

describe('toCsv', () => {
	it('writes rows, leaving empty values blank', () => {
		expect(
			toCsv([
				['Fiscal year', 'Amount'],
				['2024-25', 92322000000],
				['2023-24', null]
			])
		).toBe('Fiscal year,Amount\r\n2024-25,92322000000\r\n2023-24,\r\n');
	});

	it('quotes values with commas or quotes', () => {
		expect(toCsv([['Mining, manufacturing', 'say "hi"']])).toBe(
			'"Mining, manufacturing","say ""hi"""\r\n'
		);
	});
});
