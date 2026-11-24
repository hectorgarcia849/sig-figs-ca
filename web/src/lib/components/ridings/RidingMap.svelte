<script lang="ts">
	// The map of the ridings, each coloured by its winner's party.
	//
	// The map file is already flat (Statistics Canada's Lambert projection, in
	// metres), so it is drawn as it is: only flipped (north up) and scaled to fit.
	// Moving and zooming (drag, scroll, pinch, the buttons, the keyboard) move one
	// group of shapes; borders keep the same width at every zoom.
	//
	// Choosing a riding (click or tap) calls onselect. The page then passes it back
	// as `selected`, and the map zooms to it; choosing a province zooms to that.
	//
	// The map is one stop for the keyboard (arrow keys move, + and - zoom). Every
	// riding can also be reached through the search and the table, which select it here.
	import { onMount, untrack } from 'svelte';
	import { geoIdentity, geoPath } from 'd3-geo';
	import { select } from 'd3-selection';
	import 'd3-transition';
	import { zoom, zoomIdentity, type ZoomTransform } from 'd3-zoom';
	import { feature, mesh } from 'topojson-client';
	import type { GeometryCollection, Topology } from 'topojson-specification';

	interface Props {
		topology: Topology;
		/** The fill colour of each riding, by its number. */
		colourOf: (code: string) => string;
		/** Whether a riding passes the filters; the others are faded. */
		isShown: (code: string) => boolean;
		/** The words shown when the pointer is over a riding, e.g. "Avalon – Liberal". */
		describe: (code: string) => string;
		/** Whether a riding is in a province or territory ("on"), for zooming to it. */
		isInProvince: (code: string, province: string) => boolean;
		selected: string | null;
		province: string | null;
		onselect: (code: string) => void;
		text: { map: string; help: string; zoomIn: string; zoomOut: string; showAll: string };
	}

	let {
		topology,
		colourOf,
		isShown,
		describe,
		isInProvince,
		selected,
		province,
		onselect,
		text
	}: Props = $props();

	// The map's own units: 1000 wide, as tall as Canada's shape needs.
	const WIDTH = 1000;
	const MAX_ZOOM = 400;
	// How much of the view a chosen riding or province fills.
	const RIDING_FILL = 0.35;
	const PROVINCE_FILL = 0.9;
	// One arrow-key press moves this share of the view; + and - zoom by this factor.
	const PAN_SHARE = 0.1;
	const ZOOM_STEP = 1.6;
	const ANIMATION_MS = 600;
	// A riding's number starts with its province's two-digit code.
	const PROVINCE_DIGITS = 2;

	const LAYER = 'ridings';
	const ridingsLayer = $derived(topology.objects[LAYER] as GeometryCollection);
	const ridingFeatures = $derived(feature(topology, ridingsLayer).features);

	// Fit the map to WIDTH, keeping its shape: measure it flipped but unscaled first.
	const everything = $derived({ type: 'FeatureCollection' as const, features: ridingFeatures });
	const aspect = $derived.by(() => {
		const [[x0, y0], [x1, y1]] = geoPath(geoIdentity().reflectY(true)).bounds(everything);
		return (y1 - y0) / (x1 - x0);
	});
	const projection = $derived(
		geoIdentity()
			.reflectY(true)
			.fitSize([WIDTH, WIDTH * aspect], everything)
	);
	const path = $derived(geoPath(projection));
	const height = $derived(Math.ceil(WIDTH * aspect));

	const shapes = $derived(
		ridingFeatures.map((each) => ({
			code: String(each.id),
			d: path(each) ?? '',
			bounds: path.bounds(each)
		}))
	);
	const shapeOf = $derived(new Map(shapes.map((shape) => [shape.code, shape])));

	const provinceOf = (code: string | number | undefined) => String(code).slice(0, PROVINCE_DIGITS);
	const ridingBorders = $derived(
		path(mesh(topology, ridingsLayer, (a, b) => a !== b && provinceOf(a.id) === provinceOf(b.id)))
	);
	const provinceBorders = $derived(
		path(mesh(topology, ridingsLayer, (a, b) => a !== b && provinceOf(a.id) !== provinceOf(b.id)))
	);
	const coastline = $derived(path(mesh(topology, ridingsLayer, (a, b) => a === b)));

	// --- Moving and zooming -------------------------------------------------------

	let svg: SVGSVGElement;
	let transform: ZoomTransform = $state(zoomIdentity);
	let ready = $state(false);

	/**
	 * Which events move the map. The mouse wheel zooms only with Ctrl (or ⌘) held,
	 * so scrolling the page over the map scrolls the page. Trackpad pinches count
	 * as Ctrl + wheel in browsers, so they still zoom. Otherwise d3's default:
	 * no right-button drags, no Ctrl-clicks.
	 */
	function movesMap(event: MouseEvent | WheelEvent): boolean {
		if (event.type === 'wheel') return event.ctrlKey || event.metaKey;
		return !event.ctrlKey && !event.button;
	}

	const behaviour = $derived(
		zoom<SVGSVGElement, unknown>()
			.filter(movesMap)
			.scaleExtent([1, MAX_ZOOM])
			.translateExtent([
				[0, 0],
				[WIDTH, height]
			])
			.on('zoom', (event: { transform: ZoomTransform }) => {
				transform = event.transform;
			})
	);

	onMount(() => {
		select(svg).call(behaviour);
		ready = true;
	});

	function reducedMotion(): boolean {
		return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	}

	/** Move the view to a transform, smoothly unless the visitor prefers less motion. */
	function moveTo(target: ZoomTransform) {
		const selection = select(svg);
		if (reducedMotion()) {
			selection.call(behaviour.transform, target);
		} else {
			selection.transition().duration(ANIMATION_MS).call(behaviour.transform, target);
		}
	}

	/** The transform that centres a box and makes it fill this share of the view. */
	function framing([[x0, y0], [x1, y1]]: [[number, number], [number, number]], fill: number) {
		const scale = Math.min(MAX_ZOOM, fill / Math.max((x1 - x0) / WIDTH, (y1 - y0) / height));
		return zoomIdentity
			.translate(WIDTH / 2, height / 2)
			.scale(Math.max(1, scale))
			.translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
	}

	/** The box around every riding of a province. */
	function provinceBounds(code: string): [[number, number], [number, number]] | null {
		const boxes = shapes
			.filter((shape) => isInProvince(shape.code, code))
			.map((shape) => shape.bounds);
		if (boxes.length === 0) return null;
		return [
			[Math.min(...boxes.map((b) => b[0][0])), Math.min(...boxes.map((b) => b[0][1]))],
			[Math.max(...boxes.map((b) => b[1][0])), Math.max(...boxes.map((b) => b[1][1]))]
		];
	}

	// Zoom to the chosen riding, else the chosen province, else all of Canada.
	$effect(() => {
		const riding = selected;
		const place = province;
		if (!ready) return;
		untrack(() => {
			const shape = riding ? shapeOf.get(riding) : undefined;
			const placeBox = place ? provinceBounds(place) : null;
			if (shape) moveTo(framing(shape.bounds, RIDING_FILL));
			else if (placeBox) moveTo(framing(placeBox, PROVINCE_FILL));
			else moveTo(zoomIdentity);
		});
	});

	function zoomBy(factor: number) {
		const selection = select(svg);
		if (reducedMotion()) selection.call(behaviour.scaleBy, factor);
		else
			selection
				.transition()
				.duration(ANIMATION_MS / 2)
				.call(behaviour.scaleBy, factor);
	}

	function onkeydown(event: KeyboardEvent) {
		const step = (PAN_SHARE * WIDTH) / transform.k;
		const moves: Record<string, [number, number]> = {
			ArrowLeft: [step, 0],
			ArrowRight: [-step, 0],
			ArrowUp: [0, step],
			ArrowDown: [0, -step]
		};
		if (event.key in moves) {
			select(svg).call(behaviour.translateBy, ...moves[event.key]);
		} else if (event.key === '+' || event.key === '=') {
			zoomBy(ZOOM_STEP);
		} else if (event.key === '-' || event.key === '_') {
			zoomBy(1 / ZOOM_STEP);
		} else {
			return;
		}
		event.preventDefault();
	}

	// --- Pointing at a riding -------------------------------------------------------

	let wrapper: HTMLDivElement;
	let hovered: { code: string; x: number; y: number } | null = $state(null);

	const codeAt = (target: EventTarget | null) =>
		(target as Element | null)?.closest('[data-code]')?.getAttribute('data-code') ?? null;

	function onpointermove(event: PointerEvent) {
		const code = codeAt(event.target);
		if (!code || event.pointerType === 'touch') {
			hovered = null;
			return;
		}
		const box = wrapper.getBoundingClientRect();
		hovered = { code, x: event.clientX - box.left, y: event.clientY - box.top };
	}

	function onclick(event: MouseEvent) {
		const code = codeAt(event.target);
		if (code) onselect(code);
	}

	const helpId = 'riding-map-help';
</script>

<div class="map" bind:this={wrapper}>
	<div class="buttons">
		<button
			type="button"
			aria-label={text.zoomIn}
			title={text.zoomIn}
			onclick={() => zoomBy(ZOOM_STEP)}>+</button
		>
		<button
			type="button"
			aria-label={text.zoomOut}
			title={text.zoomOut}
			onclick={() => zoomBy(1 / ZOOM_STEP)}>−</button
		>
		<button type="button" onclick={() => moveTo(zoomIdentity)}>{text.showAll}</button>
	</div>

	<!-- A map is a custom keyboard widget (role "application"): arrow keys move it, + and -
	     zoom it. Pointing and clicking are extras: the search and table reach every riding. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
	<svg
		bind:this={svg}
		viewBox="0 0 {WIDTH} {height}"
		role="application"
		aria-label={text.map}
		aria-describedby={helpId}
		tabindex="0"
		{onkeydown}
		{onpointermove}
		onpointerleave={() => (hovered = null)}
		{onclick}
	>
		<g transform={transform.toString()}>
			{#each shapes as shape (shape.code)}
				<path
					d={shape.d}
					data-code={shape.code}
					fill={colourOf(shape.code)}
					class:faded={!isShown(shape.code)}
				/>
			{/each}
			<path class="riding-borders" d={ridingBorders} />
			<path class="province-borders" d={provinceBorders} />
			<path class="coastline" d={coastline} />
			{#if selected && shapeOf.get(selected)}
				<path class="selected" d={shapeOf.get(selected)!.d} />
			{/if}
		</g>
	</svg>
	<p id={helpId} class="help">{text.help}</p>

	{#if hovered}
		<div class="tooltip" style:left="{hovered.x}px" style:top="{hovered.y}px" aria-hidden="true">
			{describe(hovered.code)}
		</div>
	{/if}
</div>

<style>
	.map {
		position: relative;
	}

	svg {
		display: block;
		width: 100%;
		height: auto;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		cursor: grab;
		touch-action: none;
	}

	svg:active {
		cursor: grabbing;
	}

	path {
		cursor: pointer;
	}

	path.faded {
		opacity: 0.15;
	}

	.riding-borders,
	.province-borders,
	.coastline,
	.selected {
		fill: none;
		pointer-events: none;
		vector-effect: non-scaling-stroke;
		stroke-linejoin: round;
	}

	.riding-borders {
		stroke: #ffffff;
		stroke-width: 0.5;
	}

	.province-borders {
		stroke: #ffffff;
		stroke-width: 1.5;
	}

	.coastline {
		stroke: var(--color-muted);
		stroke-width: 0.4;
	}

	.selected {
		stroke: var(--color-text);
		stroke-width: 3;
	}

	.buttons {
		position: absolute;
		top: var(--space-s);
		right: var(--space-s);
		display: flex;
		gap: var(--space-xs);
	}

	.buttons button {
		min-width: 2.25rem;
		min-height: 2.25rem;
		font: inherit;
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		cursor: pointer;
	}

	.help {
		margin: var(--space-xs) 0 0;
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	.tooltip {
		position: absolute;
		transform: translate(-50%, calc(-100% - 0.75rem));
		padding: var(--space-xs) var(--space-s);
		background: var(--color-text);
		color: var(--color-background);
		border-radius: var(--radius);
		font-size: 0.875rem;
		white-space: nowrap;
		pointer-events: none;
	}
</style>
