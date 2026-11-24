<script lang="ts">
	// Find a riding by typing part of its name (English, French, or its name on
	// election day), ignoring accents and dashes. Matches appear as a list of
	// buttons under the box; pressing one chooses that riding.
	import { messages, type Language } from '#lib/i18n/index.ts';
	import { searchRidings, type RidingSummary } from '#lib/model/ridings.ts';

	interface Props {
		summaries: RidingSummary[];
		lang: Language;
		onselect: (code: string) => void;
	}

	let { summaries, lang, onselect }: Props = $props();

	const text = $derived(messages(lang).ridingsPage);
	let search = $state('');
	const matches = $derived(searchRidings(summaries, search, lang));
	const name = (summary: RidingSummary) => (lang === 'en' ? summary.name_en : summary.name_fr);

	function choose(code: string) {
		onselect(code);
		search = '';
	}

	function onkeydown(event: KeyboardEvent) {
		// Enter chooses the first match, so the keyboard needs no extra steps.
		if (event.key === 'Enter' && matches.length > 0) {
			event.preventDefault();
			choose(matches[0].code);
		}
	}
</script>

<div class="search">
	<label for="riding-search">{text.search}</label>
	<input
		id="riding-search"
		type="search"
		autocomplete="off"
		aria-describedby="riding-search-hint riding-search-count"
		bind:value={search}
		{onkeydown}
	/>
	<p id="riding-search-hint" class="hint">{text.searchHint}</p>
	<p id="riding-search-count" class="visually-hidden" role="status">
		{search.trim() ? text.matches(matches.length) : ''}
	</p>
	{#if matches.length > 0}
		<ul>
			{#each matches as summary (summary.code)}
				<li>
					<button type="button" onclick={() => choose(summary.code)}>{name(summary)}</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.search {
		position: relative;
	}

	label {
		display: block;
		font-weight: bold;
	}

	input {
		width: 100%;
		max-width: 24rem;
		min-height: 2.25rem;
		padding: var(--space-xs) var(--space-s);
		font: inherit;
		border: 1px solid var(--color-muted);
		border-radius: var(--radius);
	}

	.hint {
		margin: var(--space-xs) 0 0;
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	ul {
		max-width: 24rem;
		margin: var(--space-xs) 0 0;
		padding: 0;
		list-style: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
	}

	li + li {
		border-top: 1px solid var(--color-border);
	}

	button {
		width: 100%;
		padding: var(--space-s);
		font: inherit;
		text-align: left;
		color: var(--color-accent);
		background: var(--color-background);
		border: none;
		cursor: pointer;
	}

	button:hover {
		background: var(--color-surface);
	}

	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
