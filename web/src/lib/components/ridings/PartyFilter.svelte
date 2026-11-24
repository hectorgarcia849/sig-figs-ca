<script lang="ts">
	// Seats won by each party, as buttons that filter the map and table: pressing
	// a party shows only its ridings; pressing more adds theirs; "Show all parties"
	// clears the filter.
	import { formatCount } from '#lib/i18n/format.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';
	import { partyColour, partyShortName } from '#lib/model/ridings.ts';
	import type { Party } from '#lib/model/types.ts';

	interface Props {
		counts: { party: Party; seats: number }[];
		chosen: string[];
		lang: Language;
		onchange: (parties: string[]) => void;
	}

	let { counts, chosen, lang, onchange }: Props = $props();

	const text = $derived(messages(lang).ridingsPage);

	function toggle(code: string) {
		onchange(chosen.includes(code) ? chosen.filter((each) => each !== code) : [...chosen, code]);
	}
</script>

<div class="parties" role="group" aria-labelledby="seats-heading" aria-describedby="seats-note">
	<h2 id="seats-heading">{text.seats}</h2>
	<p id="seats-note" class="note">{text.partyFilterNote}</p>
	<ul>
		{#each counts as { party, seats } (party.code)}
			<li>
				<button
					type="button"
					aria-pressed={chosen.includes(party.code)}
					onclick={() => toggle(party.code)}
				>
					<span class="swatch" style:background={partyColour(party.code)} aria-hidden="true"></span>
					{text.seatCount(partyShortName(party, party.code, lang), formatCount(seats, lang))}
				</button>
			</li>
		{/each}
		{#if chosen.length > 0}
			<li>
				<button type="button" class="clear" onclick={() => onchange([])}>{text.allParties}</button>
			</li>
		{/if}
	</ul>
</div>

<style>
	h2 {
		margin: 0;
		font-size: 1rem;
	}

	.note {
		margin: 0 0 var(--space-xs);
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	ul {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		min-height: 2.25rem;
		padding: var(--space-xs) var(--space-s);
		font: inherit;
		color: var(--color-text);
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		cursor: pointer;
	}

	button[aria-pressed='true'] {
		border-color: var(--color-text);
		box-shadow: inset 0 0 0 1px var(--color-text);
		font-weight: bold;
	}

	.clear {
		color: var(--color-accent);
		text-decoration: underline;
	}

	.swatch {
		display: inline-block;
		width: 0.875rem;
		height: 0.875rem;
		border-radius: 0.15rem;
	}
</style>
