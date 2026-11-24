/**
 * The shape of each file "pst export" writes to web/data/.
 *
 * Column names match the views in schema/serving.sql. If the export changes,
 * change these to match (later they will be generated from the API).
 */

/** The four ways of counting spending. Every page says which one it shows. */
export type View = 'federal' | 'province_wide' | 'provincial_government' | 'canada';

/** Whether transfers to other governments are counted in the amount. */
export type Transfers = 'included' | 'excluded';

/** meta.json: the build the data came from, and every source. */
export interface Meta {
	build_id: string;
	built_at: string; // UTC, e.g. "2026-11-16T15:21:17"
	base_year: number; // real dollars are in this fiscal year's dollars
	first_fiscal_year: number;
	latest_fiscal_year: number;
	sources: Source[];
}

/** One Statistics Canada table or Elections Canada file behind the figures. */
export interface Source {
	source_id: string; // e.g. "statcan-10100005", "elections-ge45_results_by_candidate"
	publisher: string;
	table_number: string | null; // e.g. "10-10-0005-01"; Elections Canada files have none
	title_en: string;
	title_fr: string;
	release: string; // e.g. "2025-11-27"
	url_en: string;
	url_fr: string;
	doi: string | null; // Elections Canada files have none
	licence: string;
	licence_url: string;
}

/** jurisdictions.json: Canada and the 13 provinces and territories. */
export interface Jurisdiction {
	code: string; // "ca", "on", ...
	name_en: string;
	name_fr: string;
	kind: 'country' | 'province' | 'territory';
	sort_order: number;
}

/** functions.json: the 10 COFOG functions and their sub-functions. */
export interface GovernmentFunction {
	function_id: string; // "707" (health), "7073" (hospital services), ...
	level: 1 | 2;
	parent_id: string | null;
	name_en: string;
	name_fr: string;
	sort_order: number;
}

/** Whether a figure is the first estimate, revised, or final (null: not flagged). */
export type RevisionStatus = 'preliminary' | 'revised' | null;

/** The measures every figure is shown in. */
export interface Measures {
	amount: number; // dollars
	amount_real: number; // in base-year dollars
	amount_per_person: number;
	amount_real_per_person: number;
	percent_of_gdp: number;
	gdp_method: 'exact' | 'blended' | 'partial';
	revision_status: RevisionStatus;
	release: string;
	source_id: string;
	vector: string; // Statistics Canada's ID for the series
}

/** spending.json: one view, jurisdiction, function, fiscal year and transfers choice. */
export interface SpendingRow extends Measures {
	view: View;
	jurisdiction: string;
	function_id: string;
	fiscal_year: number; // start year: 2024 means 2024-25
	transfers: Transfers;
	transfers_to_governments: number | null;
}

/** municipal_transfers.json: what municipalities received from other governments. */
export interface MunicipalTransferRow extends Measures {
	jurisdiction: string;
	fiscal_year: number;
}

// --- What pages receive -----------------------------------------------------

/** The five measures, by name. */
export type MeasureValues = Pick<
	Measures,
	'amount' | 'amount_real' | 'amount_per_person' | 'amount_real_per_person' | 'percent_of_gdp'
>;

/**
 * One line of figures over time, as pages receive it: every list holds one
 * entry per fiscal year, in the order of the page's `years` (null where there
 * is no figure). One series comes from one Statistics Canada vector.
 */
export interface MeasureSeries {
	jurisdiction: string;
	source_id: string;
	vector: string;
	values: { [Name in keyof MeasureValues]: (number | null)[] };
	revision_status: RevisionStatus[];
	gdp_method: (Measures['gdp_method'] | null)[];
}

/** A spending series: one view, jurisdiction, function and transfers choice. */
export interface SpendingSeries extends MeasureSeries {
	view: View;
	function_id: string;
	transfers: Transfers;
	transfers_to_governments: (number | null)[];
}
