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

	// Placeholder text until the real pages are built.
	comingSoon: 'Charts and tables for this page are coming next.',
	rowsLoaded: (count: string) => `${count} rows of data loaded for this page.`
};

/** The shape every language's messages must have. */
export type Messages = typeof en;
