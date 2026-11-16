<script lang="ts">
	// The welcome page at /: both languages side by side, as on Government of
	// Canada sites. Each half is marked with its language for screen readers.
	import { resolve } from '$app/paths';
	import LanguageLinks from '#lib/components/LanguageLinks.svelte';
	import { en } from '#lib/i18n/en.ts';
	import { fr } from '#lib/i18n/fr.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<LanguageLinks
	siteUrl={data.siteUrl}
	address="/"
	addresses={{ en: '/en', fr: '/fr' }}
	includeWelcomePage
/>

<svelte:head>
	<title>{en.siteName} | {fr.siteName}</title>
	<meta name="description" content={en.siteDescription} />
</svelte:head>

<main class="welcome">
	<section lang="en">
		<h1>{en.siteName}</h1>
		<p>{en.siteDescription}</p>
		<a class="button" href={resolve('/[lang=lang]', { lang: 'en' })}>English</a>
	</section>
	<section lang="fr">
		<h1>{fr.siteName}</h1>
		<p>{fr.siteDescription}</p>
		<a class="button" href={resolve('/[lang=lang]', { lang: 'fr' })}>Français</a>
	</section>
</main>

<style>
	.welcome {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-l);
		max-width: var(--page-width);
		margin: 0 auto;
		padding: var(--space-xl) var(--space-m);
	}

	.button {
		display: inline-block;
		padding: var(--space-s) var(--space-m);
		background: var(--color-accent);
		color: var(--color-on-accent);
		border-radius: var(--radius);
		text-decoration: none;
		font-weight: 600;
	}
</style>
