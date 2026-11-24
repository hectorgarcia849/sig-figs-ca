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
	termsOfUse: 'conditions d’utilisation',

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
			`${functionName}, ${year} : ${share} des dépenses par les provinces et territoires`,
		compareOverTime: (name: string, phrase: string, firstYear: string, lastYear: string) =>
			`${name} ${phrase}, de ${firstYear} à ${lastYear}`
	},
	compare: 'Comparer',
	compareTitle: 'Comparer les gouvernements',
	compareIntro:
		"Comparez des gouvernements côte à côte : choisissez-en jusqu'à 7, les dépenses à examiner et une mesure. L'adresse conserve vos choix : la copier permet de partager la comparaison.",
	comparePage: {
		governments: 'Gouvernements',
		groups: {
			federal: 'Fédéral',
			provinces: 'Provinces',
			territories: 'Territoires',
			combined: 'Ensembles'
		},
		limit: (count: number) =>
			`Jusqu'à ${count} à la fois : désélectionnez-en un pour en choisir un autre.`,
		spendingOn: 'Dépenses examinées',
		total: 'Dépenses totales',
		wholeFunction: (name: string) => `${name} (ensemble)`,
		provinces: 'Provinces et territoires',
		provincialGovernmentNote:
			'Les provinces et territoires sont comptés comme leur gouvernement seul, sans leurs municipalités, hôpitaux, conseils scolaires, universités et collèges.',
		copyLink: 'Copier le lien vers cette comparaison',
		linkCopied: 'Lien copié.',
		copyFailed: "Impossible de copier le lien : copiez plutôt l'adresse dans le navigateur.",
		loading: 'Chargement des chiffres…',
		loadFailed:
			"Les chiffres n'ont pas pu être chargés. Vérifiez votre connexion et rechargez la page.",
		noneChosen: 'Choisissez au moins un gouvernement à comparer.',
		noFigures: (names: string) => `Aucun chiffre avec ces choix pour : ${names}.`,
		changeHeading: (from: string, to: string) => `Variation de ${from} à ${to}`,
		change: 'Variation',
		compareGovernments: 'Comparer les gouvernements pour cette fonction',
		compareWithOthers: "Comparer avec d'autres provinces et territoires"
	},
	ridings: 'Circonscriptions',
	ridingsTitle: 'Circonscriptions fédérales',
	ridingsPage: {
		intro: (count: string, election: string, day: string) =>
			`Qui a remporté chacune des ${count} circonscriptions fédérales du Canada à la ${election}, le ${day}.`,
		electedNote:
			'Indique qui a été élu ce jour-là. Les élections partielles qui ont suivi et les députés qui ont changé de parti ne sont pas encore indiqués.',
		seats: 'Sièges remportés',
		seatCount: (party: string, seats: string) => `${party} : ${seats}`,
		partyFilterNote: 'Choisissez des partis pour n’afficher que leurs circonscriptions.',
		allParties: 'Afficher tous les partis',
		province: 'Province ou territoire',
		allProvinces: 'Tout le Canada',
		search: 'Trouver une circonscription',
		searchHint: 'Tapez une partie de son nom, en français ou en anglais.',
		matches: (count: number) =>
			count === 0
				? 'Aucune circonscription ne correspond.'
				: count === 1
					? '1 circonscription correspond.'
					: `${count} circonscriptions correspondent.`,
		map: 'Carte des circonscriptions',
		mapHelp:
			'Chaque circonscription est colorée selon le parti de son élu. Faites glisser pour déplacer la carte ; pincez, ou faites défiler en tenant Ctrl (⌘ sur Mac), pour zoomer. Au clavier : les flèches déplacent, plus et moins zooment. Chaque circonscription figure aussi dans le tableau ci-dessous.',
		zoomIn: 'Zoom avant',
		zoomOut: 'Zoom arrière',
		showAll: 'Afficher tout le Canada',
		mapLoading: 'Chargement de la carte…',
		mapLoadFailed:
			'La carte n’a pas pu être chargée. Vérifiez votre connexion et rechargez la page. Le tableau ci-dessous présente chaque circonscription.',
		choose:
			'Choisissez une circonscription sur la carte, ou trouvez-la par son nom, pour voir son résultat.',
		close: 'Fermer',
		renamed: (name: string) => `Appelée ${name} à l’élection de 2025.`,
		elected: 'Élu(e)',
		reElected: 'Réélu(e)',
		won: (votes: string, points: string) => `Majorité de ${votes} voix (${points} points).`,
		turnout: (percent: string) => `Participation : ${percent}.`,
		candidates: 'Candidats',
		candidate: 'Candidat(e)',
		party: 'Parti',
		votes: 'Voix',
		share: 'Part',
		candidatesLoading: 'Chargement de tous les candidats…',
		candidatesLoadFailed: 'Les autres candidats n’ont pas pu être chargés.',
		source: 'Source : Élections Canada,',
		mapSource:
			'Limites des circonscriptions : Élections Canada. Littoral : Ressources naturelles Canada, Atlas du Canada.',
		table: 'Toutes les circonscriptions',
		tableShown: (shown: string, total: string) =>
			`${shown} circonscriptions sur ${total} affichées.`,
		riding: 'Circonscription',
		winner: 'Élu(e)',
		margin: 'Majorité',
		turnoutColumn: 'Participation',
		showOnMap: (name: string) => `Afficher ${name} sur la carte`
	},
	privacy: 'Confidentialité',
	notFound: {
		title: 'Page introuvable',
		text: "Il n'y a aucune page à cette adresse. Elle a peut-être été déplacée, ou l'adresse contient une erreur.",
		home: "Aller à la page d'accueil en français"
	},
	licenceStatement:
		'Contient des renseignements de Statistique Canada, utilisés en vertu de la Licence du gouvernement ouvert – Canada. Cela ne constitue pas une approbation de ce site par Statistique Canada :'
};
