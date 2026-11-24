<script lang="ts">
	// Every riding that passes the filters, as a table: the map's equivalent for
	// screen readers and keyboards, and a way to scan all results at once.
	// Each riding's name is a button that shows it on the map.
	import { formatCount, formatPercent } from '#lib/i18n/format.ts';
	import { localName, messages, type Language } from '#lib/i18n/index.ts';
	import { partyColour, partyShortName, type RidingSummary } from '#lib/model/ridings.ts';
	import type { Jurisdiction, Party } from '#lib/model/types.ts';

	interface Props {
		rows: RidingSummary[];
		total: number;
		parties: Party[];
		jurisdictions: Jurisdiction[];
		lang: Language;
		onselect: (code: string) => void;
	}

	let { rows, total, parties, jurisdictions, lang, onselect }: Props = $props();

	const text = $derived(messages(lang).ridingsPage);
	const partyOf = (code: string) => parties.find((party) => party.code === code);
	const placeName = (code: string) => {
		const place = jurisdictions.find((each) => each.code === code);
		return place ? localName(place, lang) : code;
	};
	const name = (summary: RidingSummary) => (lang === 'en' ? summary.name_en : summary.name_fr);
</script>

<section aria-labelledby="table-heading">
	<h2 id="table-heading">{text.table}</h2>
	<p class="count" role="status">
		{text.tableShown(formatCount(rows.length, lang), formatCount(total, lang))}
	</p>
	<div class="scroll">
		<table>
			<thead>
				<tr>
					<th scope="col">{text.riding}</th>
					<th scope="col">{text.province}</th>
					<th scope="col">{text.winner}</th>
					<th scope="col">{text.party}</th>
					<th scope="col" class="number">{text.share}</th>
					<th scope="col" class="number">{text.margin}</th>
					<th scope="col" class="number">{text.turnoutColumn}</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as summary (summary.code)}
					<tr>
						<th scope="row">
							<button
								type="button"
								aria-label={text.showOnMap(name(summary))}
								onclick={() => onselect(summary.code)}>{name(summary)}</button
							>
						</th>
						<td>{placeName(summary.jurisdiction)}</td>
						<td>{summary.winner}</td>
						<td>
							<span class="swatch" style:background={partyColour(summary.party)} aria-hidden="true"
							></span>
							{partyShortName(partyOf(summary.party), summary.party, lang)}
						</td>
						<td class="number">{formatPercent(summary.share, lang)}</td>
						<td class="number">{formatCount(summary.marginVotes, lang)}</td>
						<td class="number">{formatPercent(summary.turnout, lang)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<style>
	h2 {
		margin-bottom: 0;
	}

	.count {
		margin-top: var(--space-xs);
		color: var(--color-muted);
	}

	.scroll {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	th,
	td {
		padding: var(--space-xs) var(--space-s);
		text-align: left;
		border-bottom: 1px solid var(--color-border);
		white-space: nowrap;
	}

	tbody th {
		font-weight: normal;
		white-space: normal;
	}

	button {
		padding: 0;
		font: inherit;
		text-align: left;
		color: var(--color-accent);
		text-decoration: underline;
		background: none;
		border: none;
		cursor: pointer;
	}

	.number {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.swatch {
		display: inline-block;
		width: 0.75rem;
		height: 0.75rem;
		margin-right: 0.25rem;
		border-radius: 0.15rem;
		vertical-align: -0.05rem;
	}
</style>
