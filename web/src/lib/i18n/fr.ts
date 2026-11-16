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

	comingSoon: 'Les graphiques et tableaux de cette page arrivent bientôt.',
	seriesLoaded: (count: string) => `${count} séries de données chargées pour cette page.`
};
