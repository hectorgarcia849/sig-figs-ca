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
	termsOfUse: 'terms of use',

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
			`${functionName} in ${year}: ${share} spent by provinces and territories`,
		compareOverTime: (name: string, phrase: string, firstYear: string, lastYear: string) =>
			`${name} ${phrase}, ${firstYear} to ${lastYear}`
	},
	compare: 'Compare',
	compareTitle: 'Compare governments',
	compareIntro:
		'Put governments side by side: choose up to 7, what spending to look at, and a measure. The address keeps your choices, so copying it shares the comparison.',
	comparePage: {
		governments: 'Governments',
		groups: {
			federal: 'Federal',
			provinces: 'Provinces',
			territories: 'Territories',
			combined: 'Combined'
		},
		limit: (count: number) => `Up to ${count} at once: unselect one to choose another.`,
		spendingOn: 'Spending on',
		total: 'Total spending',
		wholeFunction: (name: string) => `${name} (all)`,
		provinces: 'Provinces and territories',
		provincialGovernmentNote:
			'Provinces and territories are counted as their governments alone, without their municipalities, hospitals, school boards, universities and colleges.',
		copyLink: 'Copy link to this comparison',
		linkCopied: 'Link copied.',
		copyFailed: 'Could not copy the link: copy the address from the browser instead.',
		loading: 'Loading figures…',
		loadFailed: 'The figures could not be loaded. Check your connection and reload the page.',
		noneChosen: 'Choose at least one government to compare.',
		noFigures: (names: string) => `No figures with these choices for: ${names}.`,
		changeHeading: (from: string, to: string) => `Change from ${from} to ${to}`,
		change: 'Change',
		compareGovernments: 'Compare governments on this function',
		compareWithOthers: 'Compare with other provinces and territories'
	},
	ridings: 'Ridings',
	ridingsTitle: 'Federal ridings',
	ridingsPage: {
		intro: (count: string, election: string, day: string) =>
			`Who won each of Canada's ${count} federal ridings at the ${election}, on ${day}.`,
		electedNote:
			'Shows who was elected that day. Later by-elections, and MPs who changed party, are not shown yet.',
		seats: 'Seats won',
		seatCount: (party: string, seats: string) => `${party}: ${seats}`,
		partyFilterNote: 'Choose parties to show only their ridings.',
		allParties: 'Show all parties',
		province: 'Province or territory',
		allProvinces: 'All of Canada',
		search: 'Find a riding',
		searchHint: 'Type part of its name, in English or French.',
		matches: (count: number) =>
			count === 0
				? 'No riding matches.'
				: count === 1
					? '1 riding matches.'
					: `${count} ridings match.`,
		map: 'Map of the ridings',
		mapHelp:
			'Each riding is coloured by the party of its winner. Drag to move the map; pinch, or scroll while holding Ctrl (⌘ on a Mac), to zoom. With the keyboard: arrow keys move, plus and minus zoom. Every riding is also in the table below.',
		zoomIn: 'Zoom in',
		zoomOut: 'Zoom out',
		showAll: 'Show all of Canada',
		mapLoading: 'Loading the map…',
		mapLoadFailed:
			'The map could not be loaded. Check your connection and reload the page. The table below has every riding.',
		choose: 'Choose a riding on the map, or find one by name, to see its result.',
		close: 'Close',
		renamed: (name: string) => `Called ${name} at the 2025 election.`,
		elected: 'Elected',
		reElected: 'Re-elected',
		won: (votes: string, points: string) => `Won by ${votes} votes (${points} points).`,
		turnout: (percent: string) => `Turnout: ${percent}.`,
		candidates: 'Candidates',
		candidate: 'Candidate',
		party: 'Party',
		votes: 'Votes',
		share: 'Share',
		candidatesLoading: 'Loading every candidate…',
		candidatesLoadFailed: 'The other candidates could not be loaded.',
		source: 'Source: Elections Canada,',
		mapSource:
			'Riding boundaries: Elections Canada. Coastline: Natural Resources Canada, Atlas of Canada.',
		table: 'Every riding',
		tableShown: (shown: string, total: string) => `${shown} of ${total} ridings shown.`,
		riding: 'Riding',
		winner: 'Winner',
		margin: 'Margin',
		turnoutColumn: 'Turnout',
		showOnMap: (name: string) => `Show ${name} on the map`
	},
	privacy: 'Privacy',
	notFound: {
		title: 'Page not found',
		text: 'There is no page at this address. It may have moved, or the address may be mistyped.',
		home: 'Go to the English home page'
	},
	licenceStatement:
		'Contains information from Statistics Canada, used under the Open Government Licence – Canada. This does not constitute an endorsement by Statistics Canada of this site:'
};

/** The shape every language's messages must have. */
export type Messages = typeof en;
