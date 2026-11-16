<!-- The methodology, in English. The French version (MethodologyFr.svelte) says the same. -->
<section>
	<h2>What the figures are</h2>
	<p>
		Every figure comes from Statistics Canada's government finance statistics, which group spending
		by function of government using the United Nations classification (COFOG): ten functions, such
		as health or education, and about fifty sub-functions.
	</p>
	<p>
		The figures are <strong>operating spending</strong>: buying roads, buildings and equipment is
		not included, nor is their depreciation. This matters most for transportation and housing.
		Interest on government debt is counted under general public services. The Canada and Quebec
		Pension Plans and government business enterprises (Crown corporations) are not included.
	</p>
</section>

<section>
	<h2>Four ways of counting</h2>
	<p>Every page says which one it shows.</p>
	<dl>
		<dt>Federal government</dt>
		<dd>The federal government alone (table 10-10-0024-01), with functions and sub-functions.</dd>
		<dt>Province-wide</dt>
		<dd>
			Each province or territory together with its municipalities, hospitals and social service
			institutions, school boards, universities and colleges, with money passed among them counted
			once (table 10-10-0005-01). Provinces divide services differently between the province and its
			municipalities, so this is the fair way to compare them, and it is the default for every
			province and every comparison. "All provinces and territories" adds them all together.
		</dd>
		<dt>Provincial government only</dt>
		<dd>
			The provincial or territorial government alone (table 10-10-0024-01). Statistics Canada
			publishes the ten functions only, without sub-functions. What municipalities received from
			other governments is shown beside it (table 10-10-0020-01), never added to it, as it is not
			split by function.
		</dd>
		<dt>All governments combined</dt>
		<dd>
			Federal, provincial, territorial and local governments together, with money passed between
			governments counted once, where it is finally spent (table 10-10-0005-01).
		</dd>
	</dl>
</section>

<section>
	<h2>Transfers to other governments</h2>
	<p>
		The federal government transfers money to provinces, territories and municipalities, such as the
		Canada Health Transfer and equalization. On the federal page it can be shown two ways:
	</p>
	<ul>
		<li>
			<strong>Including transfers</strong>: as the federal government reports it. Each transfer is
			counted under the function it pays for, so the Canada Health Transfer is under health.
		</li>
		<li>
			<strong>Excluding transfers</strong>: the federal government's own programs only. No table
			publishes this by function, so it is worked out for each function as all governments combined
			minus all provinces and territories combined. It also nets out money flowing the other way,
			such as provinces paying for RCMP policing.
		</li>
	</ul>
	<p>
		The subtraction works for the ten functions but gives negative figures below them, for services
		the federal government barely provides, so sub-functions are only shown including transfers.
	</p>
</section>

<section>
	<h2>Years and revisions</h2>
	<p>
		Figures are for fiscal years, April to March: 2024-25 runs from April 2024 to March 2025.
		Municipal figures follow the calendar year, as municipalities do.
	</p>
	<p>
		Statistics Canada marks the latest year as <strong>preliminary</strong> (p) and the year before
		as <strong>revised</strong> (r); both can change in the next release. Every figure records the release
		it came from.
	</p>
</section>

<section>
	<h2>The measures</h2>
	<dl>
		<dt>Dollars</dt>
		<dd>As spent that year.</dd>
		<dt>Adjusted for inflation</dt>
		<dd>
			In the latest fiscal year's dollars, using each government's own consumer price index,
			averaged over the fiscal year. Territories use their capital city's index (Whitehorse,
			Yellowknife, Iqaluit); federal and combined figures use Canada's.
		</dd>
		<dt>Per person</dt>
		<dd>Divided by the population on July 1 of the fiscal year.</dd>
		<dt>Share of GDP</dt>
		<dd>
			Divided by gross domestic product. For Canada, the four quarters of the fiscal year are added
			up. Provincial GDP is published by calendar year only, so a fiscal year is estimated as three
			quarters of the first calendar year plus one quarter of the next. When the next year is not
			yet published, the first year is used alone, and the chart says so.
		</dd>
	</dl>
</section>

<section>
	<h2>Checks</h2>
	<p>
		Every update is checked before it is published: sub-functions add up to their function (within
		Statistics Canada's rounding to the nearest million), every government is present for every
		year, nothing is missing, inflation-adjusted figures equal plain dollars in the latest year, and
		shares of GDP are between 0 and 100%. If any check fails, nothing is published.
	</p>
</section>

<section>
	<h2>Licences</h2>
	<p>
		The figures on this site, including the CSV downloads, may be reused under the
		<!-- An external link, not a page of this site. -->
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</a>
		licence: credit this site and Statistics Canada. The site's code is under the MIT licence. Statistics
		Canada's data is used under the Open Government Licence – Canada, as stated below.
	</p>
</section>
