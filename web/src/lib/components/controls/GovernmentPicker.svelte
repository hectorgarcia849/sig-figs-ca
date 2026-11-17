<script lang="ts" module>
	/** One group of governments to pick from, e.g. the provinces. */
	export interface GovernmentGroup {
		label: string;
		options: { code: string; label: string }[];
	}
</script>

<script lang="ts">
	// Checkboxes for choosing which governments to compare, in groups
	// (federal, provinces, territories, combined). At most `max` can be chosen:
	// once that many are, the others are greyed out and a note says why.
	// Chosen governments keep the order they were picked in, so adding one
	// never changes the colours of those already on the chart.
	import { messages, type Language } from '#lib/i18n/index.ts';

	let {
		lang,
		groups,
		chosen,
		max,
		onchange
	}: {
		lang: Language;
		groups: GovernmentGroup[];
		chosen: string[];
		max: number;
		onchange: (codes: string[]) => void;
	} = $props();

	const m = $derived(messages(lang));
	const full = $derived(chosen.length >= max);
	const limitId = $props.id();

	function toggle(code: string, checked: boolean) {
		onchange(checked ? [...chosen, code] : chosen.filter((each) => each !== code));
	}
</script>

<fieldset class="governments">
	<legend>{m.comparePage.governments}</legend>
	{#each groups as group (group.label)}
		<fieldset class="group">
			<legend>{group.label}</legend>
			{#each group.options as option (option.code)}
				{@const isChosen = chosen.includes(option.code)}
				<label class:unavailable={full && !isChosen}>
					<input
						type="checkbox"
						value={option.code}
						checked={isChosen}
						disabled={full && !isChosen}
						aria-describedby={full && !isChosen ? limitId : undefined}
						onchange={(event) => toggle(option.code, event.currentTarget.checked)}
					/>
					{option.label}
				</label>
			{/each}
		</fieldset>
	{/each}
	<p class="limit" id={limitId}>{m.comparePage.limit(max)}</p>
</fieldset>

<style>
	fieldset {
		margin: 0;
		padding: 0;
		border: none;
	}

	.governments {
		padding: var(--space-s) 0;
	}

	.governments > legend {
		font-weight: 600;
		margin-bottom: var(--space-xs);
	}

	.group {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs) var(--space-m);
		margin-bottom: var(--space-s);
	}

	.group legend {
		float: left;
		min-width: 6.5rem;
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		cursor: pointer;
	}

	.unavailable {
		color: var(--color-muted);
		cursor: not-allowed;
	}

	.limit {
		margin: 0;
		color: var(--color-muted);
		font-size: 0.875rem;
	}
</style>
