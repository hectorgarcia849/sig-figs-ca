/**
 * CSV files of the figures behind a chart, for visitors to download.
 */

export type CsvValue = string | number | null;

// Starts the file so spreadsheet programs read accents (é, à) correctly.
const BYTE_ORDER_MARK = '﻿';

/** Rows (the first one being the column names) written as CSV text. */
export function toCsv(rows: CsvValue[][]): string {
	return rows.map((row) => row.map(csvField).join(',')).join('\r\n') + '\r\n';
}

/** One value, quoted when it holds a comma, a quote or a line break. Empty for null. */
function csvField(value: CsvValue): string {
	if (value === null) return '';
	const text = String(value);
	return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/** Hand a CSV file to the visitor's browser to save. Only works in the browser. */
export function downloadCsv(fileName: string, rows: CsvValue[][]): void {
	const file = new Blob([BYTE_ORDER_MARK + toCsv(rows)], { type: 'text/csv;charset=utf-8' });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(file);
	link.download = fileName;
	link.click();
	URL.revokeObjectURL(link.href);
}
