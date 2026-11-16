// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	// A stand-in for the browser's page, used to draw charts while pages are
	// built (set in hooks.server.ts, used by lib/charts/draw.ts).
	var chartDocument: Document | undefined;
}

export {};
