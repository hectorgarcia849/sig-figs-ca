<script lang="ts">
	// "Spending on": total spending, one of the 10 functions, or a sub-function.
	// Each function is a group in the list, starting with the whole function,
	// followed by its sub-functions.
	import { localName, messages, type Language } from '#lib/i18n/index.ts';
	import { TOTAL } from '#lib/model/compare.ts';
	import type { GovernmentFunction } from '#lib/model/types.ts';

	let {
		lang,
		functions,
		value,
		onchange
	}: {
		lang: Language;
		functions: GovernmentFunction[];
		value: string;
		onchange: (spending: string) => void;
	} = $props();

	const m = $derived(messages(lang));
	const id = $props.id();
	const groups = $derived(
		functions
			.filter((each) => each.level === 1)
			.map((parent) => ({
				parent,
				parts: functions.filter((each) => each.parent_id === parent.function_id)
			}))
	);
</script>

<div class="spending">
	<label for={id}>{m.comparePage.spendingOn}</label>
	<select {id} {value} onchange={(event) => onchange(event.currentTarget.value)}>
		<option value={TOTAL}>{m.comparePage.total}</option>
		{#each groups as { parent, parts } (parent.function_id)}
			<optgroup label={localName(parent, lang)}>
				<option value={parent.function_id}
					>{m.comparePage.wholeFunction(localName(parent, lang))}</option
				>
				{#each parts as part (part.function_id)}
					<option value={part.function_id}>{localName(part, lang)}</option>
				{/each}
			</optgroup>
		{/each}
	</select>
</div>

<style>
	.spending {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-s);
		padding: var(--space-s) 0;
	}

	label {
		font-weight: 600;
	}

	select {
		font: inherit;
		max-width: 100%;
		padding: var(--space-xs) var(--space-s);
	}
</style>
