/**
 * Page checks: open the built site in a real browser (Chromium) and check
 * every page. Run with "just web-e2e", which builds the site first.
 *
 * The checks use their own preview server on port 4174, so they never get in
 * the way of one already running on 4173.
 */
import { defineConfig, devices } from '@playwright/test';

const PORT = 4174;

// Paths here are relative to this file (e2e/). Results of failed checks
// (screenshots, traces) go to e2e/test-results/, which is not kept in git.
export default defineConfig({
	testDir: '.',
	outputDir: 'test-results',
	fullyParallel: true,
	reporter: 'list',
	use: { baseURL: `http://localhost:${PORT}` },
	webServer: {
		cwd: '..',
		command: `pnpm preview --port ${PORT} --strictPort`,
		port: PORT,
		reuseExistingServer: false
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
});
