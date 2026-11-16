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

	comingSoon: 'Les graphiques et tableaux de cette page arrivent bientôt.',
	rowsLoaded: (count: string) => `${count} lignes de données chargées pour cette page.`
};
