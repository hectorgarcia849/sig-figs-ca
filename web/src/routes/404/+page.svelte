<script lang="ts">
	// "Page not found", in both languages side by side: the address that was not
	// found may not say which language the visitor reads.
	import { resolve } from '$app/paths';
	import { en } from '#lib/i18n/en.ts';
	import { fr } from '#lib/i18n/fr.ts';
</script>

<svelte:head>
	<title>{en.notFound.title} | {fr.notFound.title}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="not-found">
	<section lang="en">
		<h1>{en.notFound.title}</h1>
		<p>{en.notFound.text}</p>
		<a href={resolve('/[lang=lang]', { lang: 'en' })}>{en.notFound.home}</a>
	</section>
	<section lang="fr">
		<h1>{fr.notFound.title}</h1>
		<p>{fr.notFound.text}</p>
		<a href={resolve('/[lang=lang]', { lang: 'fr' })}>{fr.notFound.home}</a>
	</section>
</main>

<style>
	.not-found {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-l);
		max-width: var(--page-width);
		margin: 0 auto;
		padding: var(--space-xl) var(--space-m);
	}
</style>
