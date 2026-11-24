<script lang="ts">
	// Federal ridings: who won each riding at the latest general election.
	//
	//     seats per party (also the party filter), province picker, riding search
	//     the map, coloured by party, with the chosen riding's result beside it
	//     every riding as a table
	//
	// The choices (riding, parties, province) live in the address, like Compare:
	// read once the page opens, rewritten whenever one changes.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Switches from '#lib/components/controls/Switches.svelte';
	import PartyFilter from '#lib/components/ridings/PartyFilter.svelte';
	import RidingMap from '#lib/components/ridings/RidingMap.svelte';
	import RidingPanel from '#lib/components/ridings/RidingPanel.svelte';
	import RidingSearch from '#lib/components/ridings/RidingSearch.svelte';
	import RidingTable from '#lib/components/ridings/RidingTable.svelte';
	import { formatCount, formatDate } from '#lib/i18n/format.ts';
	import { localName, messages } from '#lib/i18n/index.ts';
	import { provincesAndTerritories } from '#lib/model/governments.ts';
	import {
		DEFAULT_VIEW,
		partyColour,
		partyShortName,
		passesFilters,
		readRidingView,
		ridingViewQuery,
		seatCounts,
		type CandidateResult,
		type RidingView
	} from '#lib/model/ridings.ts';
	import type { Topology } from 'topojson-specification';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const m = $derived(messages(data.lang));
	const text = $derived(m.ridingsPage);
	const places = $derived(provincesAndTerritories(data.jurisdictions));
	const summaryOf = $derived(new Map(data.summaries.map((summary) => [summary.code, summary])));
	const partyOf = (code: string) => data.parties.find((party) => party.code === code);
	const ridingName = (code: string) => {
		const summary = summaryOf.get(code);
		return summary ? (data.lang === 'en' ? summary.name_en : summary.name_fr) : code;
	};

	// The source line: Elections Canada's results by candidate for this election.
	const source = $derived(
		data.sources.find(
			(each) => each.source_id === `elections-${data.election.code}_results_by_candidate`
		)
	);

	// --- The choices --------------------------------------------------------------

	// Built with nothing chosen; the address's choices replace it once the page
	// opens (an address's query cannot be read while pages are built ahead of time).
	let view: RidingView = $state({ ...DEFAULT_VIEW });
	let addressRead = $state(false);

	onMount(() => {
		view = readRidingView(new URLSearchParams(location.search), {
			ridings: data.summaries.map((summary) => summary.code),
			parties: data.parties.map((party) => party.code),
			provinces: places.map((place) => place.code)
		});
		addressRead = true;
		loadMap();
		loadCandidates();
	});

	// Keep the address in step with the choices, without reloading the page or
	// adding a history entry for every click.
	$effect(() => {
		if (!addressRead) return;
		const query = ridingViewQuery(view);
		if (location.search === (query ? `?${query}` : '')) return;
		const address =
			resolve('/[lang=lang]/ridings', { lang: data.lang }) + (query ? `?${query}` : '');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved above, plus the query
		goto(address, { replace: true, shallow: true });
	});

	let mapArea: HTMLElement;

	/** Choose a riding. From the search or the table, also bring the map into view. */
	function chooseRiding(code: string | null, bringMapIntoView = false) {
		view = { ...view, riding: code };
		if (code && bringMapIntoView) {
			const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
			mapArea.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
		}
	}

	// --- The map and the candidates, loaded once the page opens -------------------

	let topology = $state<Topology | null>(null);
	let mapFailed = $state(false);
	let candidates = $state<CandidateResult[] | null>(null);
	let candidatesFailed = $state(false);

	async function loadJson<T>(address: string): Promise<T> {
		const response = await fetch(address);
		if (!response.ok) throw new Error(`${response.status} for ${address}`);
		return (await response.json()) as T;
	}

	function loadMap() {
		loadJson<Topology>(resolve('/data/ridings/map.json'))
			.then((content) => (topology = content))
			.catch(() => (mapFailed = true));
	}

	function loadCandidates() {
		loadJson<CandidateResult[]>(resolve('/data/ridings/candidates.json'))
			.then((content) => (candidates = content))
			.catch(() => (candidatesFailed = true));
	}

	// --- What is shown ------------------------------------------------------------

	const counts = $derived(seatCounts(data.summaries, data.parties));
	const shownRows = $derived(data.summaries.filter((summary) => passesFilters(summary, view)));
	const shownCodes = $derived(new Set(shownRows.map((summary) => summary.code)));
	const selected = $derived(view.riding ? summaryOf.get(view.riding) : undefined);
	const selectedCandidates = $derived(
		selected && candidates
			? candidates.filter(
					(each) => each.election === data.election.code && each.riding === selected.code
				)
			: null
	);
	const placeName = (code: string) => {
		const place = data.jurisdictions.find((each) => each.code === code);
		return place ? localName(place, data.lang) : code;
	};

	const intro = $derived(
		text.intro(
			formatCount(data.summaries.length, data.lang),
			localName(data.election, data.lang),
			formatDate(data.election.voting_day, data.lang)
		)
	);
</script>

<svelte:head>
	<title>{m.ridingsTitle} | {m.siteName}</title>
	<meta name="description" content={intro} />
</svelte:head>

<h1>{m.ridingsTitle}</h1>
<p class="intro">{intro}</p>
<p class="note">{text.electedNote}</p>

<Switches>
	<PartyFilter
		{counts}
		chosen={view.parties}
		lang={data.lang}
		onchange={(parties) => (view = { ...view, parties })}
	/>
	<div class="pickers">
		<label>
			<span>{text.province}</span>
			<select
				value={view.province ?? ''}
				onchange={(event) =>
					(view = { ...view, riding: null, province: event.currentTarget.value || null })}
			>
				<option value="">{text.allProvinces}</option>
				{#each places as place (place.code)}
					<option value={place.code}>{localName(place, data.lang)}</option>
				{/each}
			</select>
		</label>
		<RidingSearch
			summaries={data.summaries}
			lang={data.lang}
			onselect={(code) => chooseRiding(code, true)}
		/>
	</div>
</Switches>

<div class="layout" class:chosen={selected}>
	<div class="map-area" bind:this={mapArea}>
		{#if topology}
			<RidingMap
				{topology}
				colourOf={(code) => partyColour(summaryOf.get(code)?.party ?? '')}
				isShown={(code) => shownCodes.has(code)}
				isInProvince={(code, province) => summaryOf.get(code)?.jurisdiction === province}
				describe={(code) => {
					const party = summaryOf.get(code)?.party ?? '';
					return `${ridingName(code)} – ${partyShortName(partyOf(party), party, data.lang)}`;
				}}
				selected={view.riding}
				province={view.province}
				onselect={(code) => chooseRiding(code)}
				text={{
					map: text.map,
					help: text.mapHelp,
					zoomIn: text.zoomIn,
					zoomOut: text.zoomOut,
					showAll: text.showAll
				}}
			/>
		{:else}
			<p class="map-status" role="status">{mapFailed ? text.mapLoadFailed : text.mapLoading}</p>
		{/if}
		<p class="map-source">{text.mapSource}</p>
	</div>

	<div class="side">
		{#if selected}
			<RidingPanel
				summary={selected}
				provinceName={placeName(selected.jurisdiction)}
				candidates={selectedCandidates}
				{candidatesFailed}
				parties={data.parties}
				{source}
				lang={data.lang}
				onclose={() => chooseRiding(null)}
			/>
		{:else}
			<p class="choose">{text.choose}</p>
		{/if}
	</div>
</div>

<RidingTable
	rows={shownRows}
	total={data.summaries.length}
	parties={data.parties}
	jurisdictions={data.jurisdictions}
	lang={data.lang}
	onselect={(code) => chooseRiding(code, true)}
/>

<style>
	.intro {
		max-width: 48rem;
		font-size: 1.125rem;
	}

	.note,
	.map-source,
	.choose {
		color: var(--color-muted);
	}

	.note {
		max-width: 48rem;
	}

	.pickers {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-m);
		margin-top: var(--space-m);
	}

	.pickers label span {
		display: block;
		font-weight: bold;
	}

	select {
		min-height: 2.25rem;
		font: inherit;
	}

	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 22rem;
		gap: var(--space-m);
		align-items: start;
	}

	.map-area {
		scroll-margin-top: var(--space-m);
	}

	.map-status {
		padding: var(--space-xl) var(--space-m);
		text-align: center;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
	}

	.map-source {
		margin: var(--space-xs) 0 0;
		font-size: 0.875rem;
	}

	.choose {
		padding: var(--space-m);
		border: 1px dashed var(--color-border);
		border-radius: var(--radius);
	}

	/* Phones and narrow windows: the map takes the full width, and a chosen
	   riding's result slides up from the bottom of the screen. */
	@media (max-width: 52rem) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
		}

		.layout:not(.chosen) .side {
			display: none;
		}

		.layout.chosen .side {
			position: fixed;
			inset: auto 0 0 0;
			z-index: 10;
			max-height: 55vh;
			overflow-y: auto;
			box-shadow: 0 -0.25rem 1rem rgb(0 0 0 / 0.2);
		}
	}
</style>
