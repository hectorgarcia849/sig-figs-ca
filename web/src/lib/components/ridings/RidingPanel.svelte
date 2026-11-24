<script lang="ts">
	// One riding's result: its name (and its name on election day, if renamed),
	// province, winner, margin and turnout, then every candidate. The candidates
	// arrive after the page opens; until then, only the winner is shown.
	import { formatCount, formatPercent } from '#lib/i18n/format.ts';
	import { messages, type Language } from '#lib/i18n/index.ts';
	import {
		partyColour,
		partyShortName,
		type CandidateResult,
		type RidingSummary
	} from '#lib/model/ridings.ts';
	import type { Party, Source } from '#lib/model/types.ts';

	interface Props {
		summary: RidingSummary;
		provinceName: string;
		/** Every candidate in this riding, most votes first; null while loading. */
		candidates: CandidateResult[] | null;
		candidatesFailed: boolean;
		parties: Party[];
		source: Source | undefined;
		lang: Language;
		onclose: () => void;
	}

	let {
		summary,
		provinceName,
		candidates,
		candidatesFailed,
		parties,
		source,
		lang,
		onclose
	}: Props = $props();

	const m = $derived(messages(lang));
	const text = $derived(m.ridingsPage);
	const partyOf = (code: string) => parties.find((party) => party.code === code);
	const partyName = (code: string) => {
		const party = partyOf(code);
		return party ? (lang === 'en' ? party.name_en : party.name_fr) : code;
	};
	const name = $derived(lang === 'en' ? summary.name_en : summary.name_fr);
	const nameThen = $derived(
		summary.nameAtElection
			? lang === 'en'
				? summary.nameAtElection.en
				: summary.nameAtElection.fr
			: null
	);
	const decimal = (value: number) =>
		new Intl.NumberFormat(lang === 'en' ? 'en-CA' : 'fr-CA', {
			minimumFractionDigits: 1,
			maximumFractionDigits: 1
		}).format(value);
</script>

<section class="panel" aria-labelledby="riding-name">
	<div class="heading">
		<h2 id="riding-name">{name}</h2>
		<button type="button" class="close" onclick={onclose}>{text.close}</button>
	</div>
	<p class="place">{provinceName}</p>
	{#if nameThen}
		<p class="renamed">{text.renamed(nameThen)}</p>
	{/if}

	<p class="winner">
		<span class="swatch" style:background={partyColour(summary.party)} aria-hidden="true"></span>
		<span>
			<strong>{summary.winner}</strong>, {partyName(summary.party)}<br />
			{summary.incumbent ? text.reElected : text.elected},
			{formatPercent(summary.share, lang)}
		</span>
	</p>
	<p>
		{text.won(formatCount(summary.marginVotes, lang), decimal(summary.marginPct))}
		{text.turnout(formatPercent(summary.turnout, lang))}
	</p>

	<h3>{text.candidates}</h3>
	{#if candidates}
		<table>
			<thead>
				<tr>
					<th scope="col">{text.candidate}</th>
					<th scope="col">{text.party}</th>
					<th scope="col" class="number">{text.votes}</th>
					<th scope="col" class="number">{text.share}</th>
				</tr>
			</thead>
			<tbody>
				{#each candidates as candidate (candidate.candidate)}
					<tr class:elected={candidate.elected}>
						<th scope="row">{candidate.candidate}</th>
						<td>
							<span
								class="swatch small"
								style:background={partyColour(candidate.party)}
								aria-hidden="true"
							></span>
							{partyShortName(partyOf(candidate.party), candidate.party, lang)}
						</td>
						<td class="number">{formatCount(candidate.votes, lang)}</td>
						<td class="number">{formatPercent(candidate.share, lang)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<p class="status" role="status">
			{candidatesFailed ? text.candidatesLoadFailed : text.candidatesLoading}
		</p>
	{/if}

	{#if source}
		<p class="source">
			{text.source}
			<!-- External links to Elections Canada, not pages of this site. -->
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
			<a href={lang === 'en' ? source.url_en : source.url_fr}
				>{lang === 'en' ? source.title_en : source.title_fr}</a
			>
			(<!-- eslint-disable-next-line svelte/no-navigation-without-resolve --><a
				href={source.licence_url}>{m.termsOfUse}</a
			>).
		</p>
	{/if}
</section>

<style>
	.panel {
		padding: var(--space-m);
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
	}

	.heading {
		display: flex;
		align-items: start;
		justify-content: space-between;
		gap: var(--space-s);
	}

	h2 {
		margin: 0;
		font-size: 1.25rem;
	}

	h3 {
		margin: var(--space-m) 0 var(--space-xs);
		font-size: 1rem;
	}

	.close {
		font: inherit;
		background: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		cursor: pointer;
	}

	.place,
	.renamed,
	.status,
	.source {
		color: var(--color-muted);
	}

	.place {
		margin-top: var(--space-xs);
	}

	.source {
		font-size: 0.875rem;
	}

	.winner {
		display: flex;
		gap: var(--space-s);
		align-items: start;
	}

	.swatch {
		flex: none;
		display: inline-block;
		width: 1rem;
		height: 1rem;
		margin-top: 0.2rem;
		border-radius: 0.15rem;
	}

	.swatch.small {
		width: 0.75rem;
		height: 0.75rem;
		margin: 0 0.25rem 0 0;
		vertical-align: -0.05rem;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	th,
	td {
		padding: var(--space-xs);
		text-align: left;
		border-bottom: 1px solid var(--color-border);
	}

	tbody th {
		font-weight: normal;
	}

	tr.elected th {
		font-weight: bold;
	}

	.number {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
</style>
