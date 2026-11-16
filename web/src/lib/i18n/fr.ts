/**
 * The site's interface text in French. Same keys as en.ts.
 */
import type { Messages } from './en.ts';

export const fr: Messages = {
	siteName: 'Suivi des dépenses publiques',
	siteDescription:
		'Ce que dépensent les gouvernements au Canada, par fonction. Chaque chiffre renvoie à sa source.',
	skipToContent: 'Passer au contenu principal',
	mainNavigation: 'Navigation principale',

	otherLanguageName: 'English',

	home: 'Accueil',
	homeTitle: 'Les dépenses publiques au Canada',
	governments: 'Gouvernements',
	governmentsTitle: 'Dépenses par gouvernement',
	functions: 'Fonctions',
	functionsTitle: 'Dépenses par fonction des administrations publiques',
	methodology: 'Méthodologie et sources',
	federalGovernment: 'Gouvernement fédéral',

	source: 'Source : Statistique Canada',
	release: 'diffusion du',
	dataBuilt: 'Données compilées le',
	licence: 'Licence du gouvernement ouvert – Canada',
	licenceUrl: 'https://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada',
	sourceTables: 'Tableaux sources',
	doi: 'DOI',

	measure: 'Mesure',
	year: 'Année',
	counting: 'Calcul',
	transfers: 'Transferts aux autres gouvernements',
	measures: {
		amount: 'Dollars',
		amount_real: 'Dollars, corrigés de l’inflation',
		amount_per_person: 'Par personne',
		amount_real_per_person: 'Par personne, corrigés de l’inflation',
		percent_of_gdp: 'Part du PIB'
	},
	views: {
		federal: 'Gouvernement fédéral',
		province_wide: 'Ensemble de la province',
		provincial_government: 'Gouvernement provincial seulement',
		canada: 'Ensemble des gouvernements'
	},
	transfersChoices: {
		included: 'Transferts compris',
		excluded: 'Transferts exclus'
	},
	transfersOnlyForFunctions:
		'L’exclusion des transferts n’est possible que pour les 10 fonctions, pas pour les sous-fonctions.',

	viewAsTable: 'Voir sous forme de tableau',
	downloadCsv: 'Télécharger le CSV',
	fiscalYear: 'Exercice',
	noFigure: 'aucun chiffre',
	preliminaryMark: 'p',
	revisedMark: 'r',
	marksExplained: 'p : chiffre provisoire, r : chiffre révisé',
	sourcePrefix: 'Source : Statistique Canada,',
	tableWord: 'tableau',
	releasedOn: (date: string) => `diffusé le ${date}`,
	vector: 'Vecteur',
	sourceTable: 'Tableau de Statistique Canada',
	revisionStatus: 'Statut de révision',
	government: 'Gouvernement',
	function: 'Fonction',
	inBaseYearDollars: (year: string) =>
		`En dollars de ${year}, corrigés de l’inflation selon l’indice des prix à la consommation de chaque gouvernement.`,
	partialGdp: (year: string) =>
		`La part du PIB pour ${year} est estimée à partir d’une seule année de PIB provincial, l’année suivante n’étant pas encore publiée.`,

	allProvinces: 'Ensemble des provinces et territoires',
	allGovernments: 'Ensemble des gouvernements',
	federalOwnSpending: 'Gouvernement fédéral, dépenses propres',

	homeIntro:
		'Ce que dépensent tous les gouvernements au Canada : fédéral, provinciaux, territoriaux et locaux, chaque dollar n’étant compté qu’une fois, là où il est finalement dépensé.',
	governmentsIntro:
		'Les dépenses de chaque gouvernement pour la dernière année. Les provinces et territoires comprennent leurs municipalités, hôpitaux, conseils scolaires, universités et collèges.',
	functionsIntro:
		'Les dépenses de l’ensemble des gouvernements, regroupées par fonction des administrations publiques (classification des Nations Unies, CFAP).',
	functionIntro:
		'Les dépenses consacrées à cette fonction par chaque province et territoire, et par l’ensemble des gouvernements.',
	viewNotes: {
		province_wide:
			'La province ou le territoire avec ses municipalités, hôpitaux, conseils scolaires, universités et collèges : la façon juste de comparer les provinces.',
		provincial_government:
			'Le gouvernement provincial ou territorial seul. Ce que les municipalités ont reçu des autres gouvernements est présenté séparément plus bas.'
	},
	transfersNotes: {
		included:
			'Comprend l’argent transféré aux provinces, aux territoires et aux municipalités, compté sous la fonction qu’il finance (le Transfert canadien en matière de santé sous la santé).',
		excluded:
			'Exclut l’argent transféré aux autres gouvernements : calculé comme l’ensemble des gouvernements moins l’ensemble des provinces et territoires.'
	},
	operatingOnly:
		'Dépenses de fonctionnement seulement : l’achat de routes, de bâtiments et d’équipement n’est pas compris, ni leur amortissement.',

	totalSpending: 'Dépenses totales',
	perPerson: 'Par personne',
	shareOfGdp: 'Part du PIB',
	changeFrom: (change: string, year: string) => `${change} par rapport à ${year}`,
	// En français, « point » prend la marque du pluriel à partir de 2.
	percentagePoints: (points: string, size: number) =>
		`${points} ${Math.abs(size) >= 2 ? 'points' : 'point'} de pourcentage`,
	transferredToOthers: 'Dont transferts aux autres gouvernements',
	transferredLeftOut: 'Transferts aux autres gouvernements (exclus ci-dessus)',
	totalReceived: 'Total reçu',
	allProvincesPerPerson: 'Ensemble des provinces et territoires, par personne',
	whoDelivers: 'Qui dépense',
	whoDeliversNote:
		'L’argent que le gouvernement fédéral transfère aux provinces, aux territoires et aux municipalités est compté là où il est finalement dépensé : les dépenses fédérales et provinciales s’additionnent donc pour donner le total.',
	functionTrendNote:
		'La courbe fédérale exclut les transferts aux autres gouvernements : cet argent figure dans la courbe des provinces, là où il est dépensé. Les deux s’additionnent pour donner l’ensemble des gouvernements.',

	subFunctions: 'Sous-fonctions',
	subFunctionsOf: 'Afficher les sous-fonctions de',
	subFunctionsUnavailable:
		'Statistique Canada ne publie pas de sous-fonctions pour les gouvernements provinciaux et territoriaux seuls. Choisissez l’ensemble de la province pour les voir.',
	subFunctionsIncludeTransfers:
		'Les sous-fonctions sont présentées transferts compris : les deux ne peuvent être séparés en deçà des 10 fonctions.',
	municipalTransfers: 'Reçu par les municipalités des autres gouvernements',
	municipalTransfersNote:
		'Surtout de la province ou du territoire, en partie du gouvernement fédéral. Présenté à côté des dépenses provinciales, jamais ajouté : Statistique Canada ne le répartit pas par fonction.',

	measurePhrases: {
		amount: 'en dollars',
		amount_real: 'en dollars corrigés de l’inflation',
		amount_per_person: 'par personne',
		amount_real_per_person: 'par personne, corrigé de l’inflation',
		percent_of_gdp: 'en part du PIB'
	},
	titles: {
		overTime: (phrase: string, from: string, firstYear: string, to: string, year: string) =>
			`Dépenses ${phrase} : de ${from} en ${firstYear} à ${to} en ${year}`,
		overTimePlain: 'Les dépenses au fil du temps',
		largest: (year: string, name: string) => `Principal domaine de dépenses en ${year} : ${name}`,
		byFunctionPlain: 'Dépenses par fonction',
		largestPart: (functionName: string, year: string, name: string) =>
			`Principale composante de « ${functionName} » en ${year} : ${name}`,
		highestPlace: (functionName: string, phrase: string, year: string, place: string) =>
			`${functionName} ${phrase}, ${year} : premier rang, ${place}`,
		provincesShare: (functionName: string, year: string, share: string) =>
			`${functionName}, ${year} : ${share} des dépenses par les provinces et territoires`
	},
	licenceStatement:
		'Contient des renseignements de Statistique Canada, utilisés en vertu de la Licence du gouvernement ouvert – Canada. Cela ne constitue pas une approbation de ce site par Statistique Canada :'
};
