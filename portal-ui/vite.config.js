import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// Proxy API calls to FastAPI during development
			// changeOrigin:false preserva el Host original (localhost:5173) para que los
			// redirects trailing-slash de FastAPI queden same-origin y no se pierda el
			// header Authorization al seguirlos en el navegador.
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: false
			},
			'/auth': {
				target: 'http://localhost:8000',
				changeOrigin: false
			}
		}
	}
});
