<!-- La méthodologie, en français. Même contenu que MethodologyEn.svelte. -->
<p class="draft">
	La version française de ce site est une première traduction, en cours de révision.
</p>

<section>
	<h2>Ce que représentent les chiffres</h2>
	<p>
		Tous les chiffres proviennent des statistiques de finances publiques de Statistique Canada, qui
		regroupent les dépenses par fonction des administrations publiques selon la classification des
		Nations Unies (CFAP) : dix fonctions, comme la santé ou l'enseignement, et une cinquantaine de
		sous-fonctions.
	</p>
	<p>
		Les chiffres portent sur les <strong>dépenses de fonctionnement</strong> : l'achat de routes, de bâtiments
		et d'équipement n'est pas compris, ni leur amortissement. Cela compte surtout pour les transports
		et le logement. Les intérêts de la dette publique sont classés dans les services publics généraux.
		Le Régime de pensions du Canada, le Régime de rentes du Québec et les entreprises publiques (sociétés
		d'État) ne sont pas compris.
	</p>
</section>

<section>
	<h2>Quatre façons de compter</h2>
	<p>Chaque page indique celle qu'elle présente.</p>
	<dl>
		<dt>Gouvernement fédéral</dt>
		<dd>
			Le gouvernement fédéral seul (tableau 10-10-0024-01), avec les fonctions et les
			sous-fonctions.
		</dd>
		<dt>Ensemble de la province</dt>
		<dd>
			Chaque province ou territoire avec ses municipalités, ses hôpitaux et établissements de
			services sociaux, ses conseils scolaires, ses universités et collèges, l'argent qui circule
			entre eux n'étant compté qu'une fois (tableau 10-10-0005-01). Les provinces répartissent les
			services différemment entre la province et ses municipalités : c'est donc la façon juste de
			les comparer, et c'est le choix par défaut pour chaque province et chaque comparaison. «
			Ensemble des provinces et territoires » les additionne tous.
		</dd>
		<dt>Gouvernement provincial seulement</dt>
		<dd>
			Le gouvernement provincial ou territorial seul (tableau 10-10-0024-01). Statistique Canada ne
			publie que les dix fonctions, sans sous-fonctions. Ce que les municipalités ont reçu des
			autres gouvernements est présenté à côté (tableau 10-10-0020-01), jamais ajouté, car ce
			montant n'est pas réparti par fonction.
		</dd>
		<dt>Ensemble des gouvernements</dt>
		<dd>
			Les gouvernements fédéral, provinciaux, territoriaux et locaux ensemble, l'argent transféré
			entre gouvernements n'étant compté qu'une fois, là où il est finalement dépensé (tableau
			10-10-0005-01).
		</dd>
	</dl>
</section>

<section>
	<h2>Transferts aux autres gouvernements</h2>
	<p>
		Le gouvernement fédéral transfère de l'argent aux provinces, aux territoires et aux
		municipalités, comme le Transfert canadien en matière de santé et la péréquation. Sur la page
		fédérale, on peut le présenter de deux façons :
	</p>
	<ul>
		<li>
			<strong>Transferts compris</strong> : tel que le gouvernement fédéral le déclare. Chaque transfert
			est compté sous la fonction qu'il finance : le Transfert canadien en matière de santé figure sous
			la santé.
		</li>
		<li>
			<strong>Transferts exclus</strong> : les programmes propres du gouvernement fédéral seulement. Aucun
			tableau ne le publie par fonction; il est donc calculé pour chaque fonction comme l'ensemble des
			gouvernements moins l'ensemble des provinces et territoires. Ce calcul retranche aussi l'argent
			qui circule en sens inverse, comme les sommes que les provinces versent pour les services de police
			de la GRC.
		</li>
	</ul>
	<p>
		Ce calcul fonctionne pour les dix fonctions, mais donne des chiffres négatifs en deçà, pour des
		services que le gouvernement fédéral fournit à peine; les sous-fonctions ne sont donc présentées
		que transferts compris.
	</p>
</section>

<section>
	<h2>Années et révisions</h2>
	<p>
		Les chiffres portent sur les exercices, d'avril à mars : 2024-2025 va d'avril 2024 à mars 2025.
		Les chiffres municipaux suivent l'année civile, comme les municipalités.
	</p>
	<p>
		Statistique Canada indique que la dernière année est <strong>provisoire</strong> (p) et l'année
		précédente <strong>révisée</strong> (r); les deux peuvent changer à la diffusion suivante. Chaque
		chiffre indique la diffusion dont il provient.
	</p>
</section>

<section>
	<h2>Les mesures</h2>
	<dl>
		<dt>Dollars</dt>
		<dd>Tels que dépensés cette année-là.</dd>
		<dt>Corrigés de l'inflation</dt>
		<dd>
			En dollars du dernier exercice, selon l'indice des prix à la consommation de chaque
			gouvernement, en moyenne sur l'exercice. Les territoires utilisent l'indice de leur capitale
			(Whitehorse, Yellowknife, Iqaluit); les chiffres fédéraux et d'ensemble utilisent celui du
			Canada.
		</dd>
		<dt>Par personne</dt>
		<dd>Divisé par la population au 1er juillet de l'exercice.</dd>
		<dt>Part du PIB</dt>
		<dd>
			Divisé par le produit intérieur brut. Pour le Canada, les quatre trimestres de l'exercice sont
			additionnés. Le PIB provincial n'est publié que par année civile : un exercice est donc estimé
			à partir des trois quarts de la première année civile et d'un quart de la suivante. Lorsque
			l'année suivante n'est pas encore publiée, la première année est utilisée seule, et le
			graphique l'indique.
		</dd>
	</dl>
</section>

<section>
	<h2>Vérifications</h2>
	<p>
		Chaque mise à jour est vérifiée avant d'être publiée : les sous-fonctions s'additionnent pour
		donner leur fonction (à l'arrondi au million près de Statistique Canada), chaque gouvernement
		est présent pour chaque année, rien ne manque, les chiffres corrigés de l'inflation égalent les
		dollars courants pour la dernière année, et les parts du PIB sont comprises entre 0 et 100 %. Si
		une vérification échoue, rien n'est publié.
	</p>
</section>

<section>
	<h2>Licences</h2>
	<p>
		Les chiffres de ce site, y compris les fichiers CSV, peuvent être réutilisés selon la licence
		<!-- Un lien externe, pas une page de ce site. -->
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href="https://creativecommons.org/licenses/by/4.0/deed.fr"
			>Creative Commons Attribution 4.0</a
		>, en citant ce site et Statistique Canada. Le code du site est publié sous la licence MIT. Les
		données de Statistique Canada sont utilisées selon la Licence du gouvernement ouvert – Canada,
		comme indiqué ci-dessous.
	</p>
</section>

<style>
	.draft {
		padding: var(--space-s) var(--space-m);
		background: var(--color-surface);
		border-left: 4px solid var(--color-focus);
	}
</style>
