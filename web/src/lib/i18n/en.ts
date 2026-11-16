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

	// Names used in particular views.
	allProvinces: 'All provinces and territories',
	allGovernments: 'All governments combined',
	federalOwnSpending: 'Federal government, own spending',

	// Pages.
	homeIntro:
		'What all governments in Canada spend: federal, provincial, territorial and local, counting each dollar once, where it is finally spent.',
	governmentsIntro:
		'Each government’s spending in the latest year. Provinces and territories include their municipalities, hospitals, school boards, universities and colleges.',
	functionsIntro:
		'Spending by all governments combined, grouped by function of government (the United Nations classification, COFOG).',
	functionIntro:
		'Spending on this function by each province and territory, and by all governments.',
	viewNotes: {
		province_wide:
			'The province or territory with its municipalities, hospitals, school boards, universities and colleges: the fair way to compare provinces.',
		provincial_government:
			'The provincial or territorial government alone. What municipalities received from other governments is shown separately below.'
	},
	transfersNotes: {
		included:
			'Includes money transferred to provinces, territories and municipalities, counted under the function it pays for (the Canada Health Transfer under health).',
		excluded:
			'Excludes money transferred to other governments: worked out as all governments combined minus all provinces and territories.'
	},
	operatingOnly:
		'Operating spending only: buying roads, buildings and equipment is not included, nor is their depreciation.',

	// Key figures.
	totalSpending: 'Total spending',
	perPerson: 'Per person',
	shareOfGdp: 'Share of GDP',
	changeFrom: (change: string, year: string) => `${change} from ${year}`,
	percentagePoints: (points: string, size: number) =>
		`${points} percentage ${Math.abs(size) === 1 ? 'point' : 'points'}`,
	transferredToOthers: 'Of which transferred to other governments',
	transferredLeftOut: 'Transferred to other governments (left out above)',
	totalReceived: 'Total received',
	allProvincesPerPerson: 'All provinces and territories, per person',
	whoDelivers: 'Who spends it',
	whoDeliversNote:
		'Money the federal government transfers to provinces, territories and municipalities is counted where it is finally spent, so federal and provincial spending add up to the total.',
	functionTrendNote:
		'The federal line excludes transfers to other governments: that money is in the provinces’ line, where it is spent. The two add up to all governments combined.',

	// Sub-functions and municipalities.
	subFunctions: 'Sub-functions',
	subFunctionsOf: 'Show the sub-functions of',
	subFunctionsUnavailable:
		'Statistics Canada does not publish sub-functions for provincial and territorial governments alone. Choose province-wide to see them.',
	subFunctionsIncludeTransfers:
		'Sub-functions are shown including transfers to other governments: the two cannot be separated below the 10 functions.',
	municipalTransfers: 'Received by municipalities from other governments',
	municipalTransfersNote:
		'Mostly from the province or territory, some from the federal government. Shown beside provincial spending, never added to it: Statistics Canada does not split it by function.',

	// Chart titles: facts only, never judgments.
	measurePhrases: {
		amount: 'in dollars',
		amount_real: 'in inflation-adjusted dollars',
		amount_per_person: 'per person',
		amount_real_per_person: 'per person, adjusted for inflation',
		percent_of_gdp: 'as a share of GDP'
	},
	titles: {
		overTime: (phrase: string, from: string, firstYear: string, to: string, year: string) =>
			`Spending ${phrase} went from ${from} in ${firstYear} to ${to} in ${year}`,
		overTimePlain: 'Spending over time',
		largest: (year: string, name: string) => `Largest area of spending in ${year}: ${name}`,
		byFunctionPlain: 'Spending by function',
		largestPart: (functionName: string, year: string, name: string) =>
			`Largest part of ${functionName} in ${year}: ${name}`,
		highestPlace: (functionName: string, phrase: string, year: string, place: string) =>
			`${functionName} ${phrase} in ${year}: highest in ${place}`,
		provincesShare: (functionName: string, year: string, share: string) =>
			`${functionName} in ${year}: ${share} spent by provinces and territories`
	},
	licenceStatement:
		'Contains information from Statistics Canada, used under the Open Government Licence – Canada. This does not constitute an endorsement by Statistics Canada of this site:'
};

/** The shape every language's messages must have. */
export type Messages = typeof en;
