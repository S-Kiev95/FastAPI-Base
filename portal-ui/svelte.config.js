import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			// Build output goes to ../app/portal/ (served by FastAPI)
			pages: '../app/portal',
			assets: '../app/portal',
			fallback: 'index.html',  // SPA fallback for client-side routing
			precompress: false,
			strict: false
		}),
		paths: {
			base: '/app'
		}
	}
};

export default config;
