<script lang="ts">
	// The frame around every page in a language: header with navigation and the
	// language switch, the page itself, and a footer naming the source.
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import LanguageLinks from '#lib/components/LanguageLinks.svelte';
	import { addressInOtherLanguage, LOCALES, messages, otherLanguage } from '#lib/i18n/index.ts';
	import type { Path } from '$app/types';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const m = $derived(messages(data.lang));
	const other = $derived(otherLanguage(data.lang));
	const builtOn = $derived(
		new Intl.DateTimeFormat(LOCALES[data.lang], { dateStyle: 'long', timeZone: 'UTC' }).format(
			new Date(`${data.build.builtAt}Z`)
		)
	);

	// Built pages already carry <html lang> (see hooks.server.ts). This keeps it
	// right when the language switch is used without a full page load.
	$effect(() => {
		document.documentElement.lang = data.lang;
	});

	// The same page in the other language: /en/governments/on <-> /fr/governments/on.
	const otherLanguageAddress = $derived(
		resolve(addressInOtherLanguage(page.url.pathname, data.lang) as Path)
	);
	const addresses = $derived({
		[data.lang]: page.url.pathname,
		[other]: otherLanguageAddress
	} as Record<typeof data.lang, string>);

	const sections = $derived([
		{ label: m.governments, href: resolve('/[lang=lang]/governments', { lang: data.lang }) },
		{ label: m.functions, href: resolve('/[lang=lang]/functions', { lang: data.lang }) },
		{ label: m.methodology, href: resolve('/[lang=lang]/methodology', { lang: data.lang }) }
	]);
</script>

<LanguageLinks
	siteUrl={data.siteUrl}
	address={page.url.pathname}
	{addresses}
	includeWelcomePage={page.url.pathname === `/${data.lang}`}
/>

<a class="skip-link" href="#main">{m.skipToContent}</a>

<header>
	<div class="bar">
		<a class="site-name" href={resolve('/[lang=lang]', { lang: data.lang })}>{m.siteName}</a>
		<nav aria-label={m.mainNavigation}>
			<ul>
				{#each sections as section (section.href)}
					<li>
						<a
							href={section.href}
							aria-current={page.url.pathname.startsWith(section.href) ? 'page' : undefined}
							>{section.label}</a
						>
					</li>
				{/each}
			</ul>
		</nav>
		<a lang={other} hreflang={other} href={otherLanguageAddress}>{m.otherLanguageName}</a>
	</div>
</header>

<main id="main">
	{@render children()}
</main>

<footer>
	<p>
		{m.source} ·
		<a href={resolve('/[lang=lang]/methodology', { lang: data.lang })}>{m.sourceTables}</a> ·
		{m.dataBuilt}
		{builtOn}
	</p>
	<p>
		<!-- An external link, not a page of this site. -->
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href={m.licenceUrl}>{m.licence}</a> ·
		<a href={resolve('/[lang=lang]/privacy', { lang: data.lang })}>{m.privacy}</a>
	</p>
</footer>

<style>
	.skip-link {
		position: absolute;
		left: var(--space-s);
		top: -3rem;
		padding: var(--space-s);
		background: var(--color-background);
	}

	.skip-link:focus {
		top: var(--space-s);
	}

	header {
		border-bottom: 1px solid var(--color-border);
	}

	.bar,
	main,
	footer {
		max-width: var(--page-width);
		margin: 0 auto;
		padding: var(--space-m);
	}

	.bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-m);
	}

	.site-name {
		font-weight: 700;
		color: var(--color-text);
		text-decoration: none;
		margin-right: auto;
	}

	nav ul {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-m);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	[aria-current='page'] {
		font-weight: 700;
	}

	footer {
		border-top: 1px solid var(--color-border);
		color: var(--color-muted);
		font-size: 0.875rem;
	}
</style>
