import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			// Build output goes to ../app/admin/ (served by FastAPI)
			pages: '../app/admin',
			assets: '../app/admin',
			fallback: 'index.html',  // SPA fallback for client-side routing
			precompress: false,
			strict: false
		}),
		paths: {
			base: '/admin'
		}
	}
};

export default config;
