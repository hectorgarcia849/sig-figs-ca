/**
 * The site's interface text in English.
 *
 * Names of governments and functions are not here: they come from Statistics
 * Canada's own English and French labels in the data. The French file must
 * have exactly the same keys, or the build fails.
 */
export const en = {
	siteName: 'Public Spending Tracker',
	siteDescription:
		'What Canadian governments spend, by function of government. Every figure links to its source.',
	skipToContent: 'Skip to main content',
	mainNavigation: 'Main navigation',

	// The link to the same page in the other language.
	otherLanguageName: 'Français',

	home: 'Home',
	homeTitle: 'Government spending in Canada',
	governments: 'Governments',
	governmentsTitle: 'Spending by government',
	functions: 'Functions',
	functionsTitle: 'Spending by function of government',
	methodology: 'Methodology and sources',
	federalGovernment: 'Federal government',

	source: 'Source: Statistics Canada',
	release: 'release',
	dataBuilt: 'Data built',
	licence: 'Open Government Licence – Canada',
	licenceUrl: 'https://open.canada.ca/en/open-government-licence-canada',
	sourceTables: 'Source tables',
	doi: 'DOI',

	// The switches.
	measure: 'Measure',
	year: 'Year',
	counting: 'Counting',
	transfers: 'Transfers to other governments',
	measures: {
		amount: 'Dollars',
		amount_real: 'Dollars, adjusted for inflation',
		amount_per_person: 'Per person',
		amount_real_per_person: 'Per person, adjusted for inflation',
		percent_of_gdp: 'Share of GDP'
	},
	views: {
		federal: 'Federal government',
		province_wide: 'Province-wide',
		provincial_government: 'Provincial government only',
		canada: 'All governments combined'
	},
	transfersChoices: {
		included: 'Including transfers',
		excluded: 'Excluding transfers'
	},
	transfersOnlyForFunctions:
		'Excluding transfers is only possible for the 10 functions, not for sub-functions.',

	// Charts and tables.
	viewAsTable: 'View as table',
	downloadCsv: 'Download CSV',
	fiscalYear: 'Fiscal year',
	noFigure: 'no figure',
	preliminaryMark: 'p',
	revisedMark: 'r',
	marksExplained: 'p: preliminary figure, r: revised figure',
	sourcePrefix: 'Source: Statistics Canada,',
	tableWord: 'table',
	releasedOn: (date: string) => `released ${date}`,
	vector: 'Vector',
	sourceTable: 'Statistics Canada table',
	revisionStatus: 'Revision status',
	government: 'Government',
	function: 'Function',
	inBaseYearDollars: (year: string) =>
		`In ${year} dollars, adjusted for inflation with each government's own consumer price index.`,
	partialGdp: (year: string) =>
		`Share of GDP for ${year} is estimated from one year of provincial GDP, as the next year is not yet published.`,

	// Placeholder text until the real pages are built.
	comingSoon: 'Charts and tables for this page are coming next.',
	seriesLoaded: (count: string) => `${count} data series loaded for this page.`
};

/** The shape every language's messages must have. */
export type Messages = typeof en;
