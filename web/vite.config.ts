import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

// The address the site is published at, with no "/" at the end. Search
// engines need full addresses (canonical and language links, the sitemap),
// so pages are built with it. The deploy script sets SITE_URL from Terraform
// (the free Firebase address now, a custom domain later); local builds use
// the preview server's address.
const LOCAL_SITE_URL = 'http://localhost:4173';
const SITE_URL = (process.env.SITE_URL ?? LOCAL_SITE_URL).replace(/\/$/, '');

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			paths: {
				origin: SITE_URL,
				// Script and style addresses start with "/", so the "page not found"
				// page works at any address it is shown for.
				relative: false
			},
			// Content security policy, added to every page as a <meta> tag. Only the
			// site's own scripts may run: SvelteKit adds a hash for each of its
			// inline scripts. Inline styles are allowed because charts carry them.
			// Rules a <meta> tag cannot set (e.g. frame-ancestors) are in firebase.json.
			csp: {
				mode: 'hash',
				directives: {
					'default-src': ['self'],
					'script-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'font-src': ['self'],
					'connect-src': ['self'],
					'object-src': ['none'],
					'base-uri': ['self'],
					'form-action': ['self']
				}
			}
		})
	],
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
