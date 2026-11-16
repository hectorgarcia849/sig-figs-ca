<script lang="ts">
	// The measure switch: dollars, adjusted for inflation, per person, share of GDP.
	import { messages, type Language } from '#lib/i18n/index.ts';
	import { MEASURES, type Measure } from '#lib/measures.ts';
	import ChoiceGroup from './ChoiceGroup.svelte';

	let {
		lang,
		value,
		onchange
	}: { lang: Language; value: Measure; onchange: (measure: Measure) => void } = $props();

	const m = $derived(messages(lang));
	const options = $derived(
		MEASURES.map((measure) => ({ value: measure, label: m.measures[measure] }))
	);
</script>

<ChoiceGroup legend={m.measure} name="measure" {options} {value} {onchange} />
