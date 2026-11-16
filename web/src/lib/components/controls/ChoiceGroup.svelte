<script lang="ts" module>
	/** One choice in the group. */
	export interface Option<Value> {
		value: Value;
		label: string;
		unavailableBecause?: string; // set to grey the option out and say why
	}
</script>

<script lang="ts" generics="Value extends string">
	// A labelled group of radio buttons: one choice out of a few, such as the
	// measure or the view. Works with a keyboard and screen readers as standard.
	// An option that does not apply is greyed out, with the reason shown.

	let {
		legend,
		name,
		options,
		value,
		onchange
	}: {
		legend: string;
		name: string; // unique on the page, e.g. "measure"
		options: Option<Value>[];
		value: Value;
		onchange: (value: Value) => void;
	} = $props();
</script>

<fieldset>
	<legend>{legend}</legend>
	{#each options as option (option.value)}
		{@const reasonId = `${name}-${option.value}-reason`}
		<label class:unavailable={option.unavailableBecause}>
			<input
				type="radio"
				{name}
				value={option.value}
				checked={option.value === value}
				disabled={Boolean(option.unavailableBecause)}
				aria-describedby={option.unavailableBecause ? reasonId : undefined}
				onchange={() => onchange(option.value)}
			/>
			{option.label}
		</label>
		{#if option.unavailableBecause}
			<span class="reason" id={reasonId}>{option.unavailableBecause}</span>
		{/if}
	{/each}
</fieldset>

<style>
	fieldset {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-s) var(--space-m);
		margin: 0;
		padding: var(--space-s) 0;
		border: none;
	}

	legend {
		float: left;
		margin-right: var(--space-s);
		font-weight: 600;
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

	.reason {
		flex-basis: 100%;
		color: var(--color-muted);
		font-size: 0.875rem;
	}
</style>
