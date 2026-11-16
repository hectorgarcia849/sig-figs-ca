// The site's full address (e.g. https://public-spend-tracker.web.app), for
// links search engines read. Pages are built with the address set in
// vite.config.ts, so this is the published address, not the build machine's.
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ url }) => ({ siteUrl: url.origin });
