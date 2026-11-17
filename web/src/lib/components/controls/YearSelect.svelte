<script lang="ts">
	// The year switch: a list of fiscal years, newest first.
	import { fiscalYearLabel } from '#lib/i18n/format.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';

	let {
		lang,
		years,
		value,
		onchange
	}: {
		lang: Language;
		years: number[];
		value: number;
		onchange: (year: number) => void;
	} = $props();

	const id = $props.id();
	const newestFirst = $derived([...years].reverse());
</script>

<div class="year">
	<label for={id}>{messages(lang).year}</label>
	<select {id} {value} onchange={(event) => onchange(Number(event.currentTarget.value))}>
		{#each newestFirst as year (year)}
			<option value={year}>{fiscalYearLabel(year, lang)}</option>
		{/each}
	</select>
</div>

<style>
	.year {
		display: flex;
		align-items: center;
		gap: var(--space-s);
		padding: var(--space-s) 0;
	}

	label {
		font-weight: 600;
	}

	select {
		font: inherit;
		padding: var(--space-xs) var(--space-s);
	}
</style>
