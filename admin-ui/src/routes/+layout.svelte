<script>
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import { getSetupStatus } from '$lib/api.js';

	let { children } = $props();
	let checking = $state(true);

	onMount(async () => {
		// Si ya estamos en /setup, no re-chequear (evita loop)
		const currentPath = $page.url.pathname;
		if (currentPath.includes('/setup')) {
			checking = false;
			return;
		}

		try {
			const status = await getSetupStatus();
			if (!status.configured) {
				// Sistema no configurado → redirigir al wizard
				goto(`${base}/setup`);
				return;
			}
		} catch (err) {
			// Si el endpoint falla, asumimos que el backend puede estar abajo
			// o el sistema no configurado; redirigimos al setup
			console.warn('Setup status check failed, redirecting to wizard', err);
			goto(`${base}/setup`);
			return;
		}
		checking = false;
	});
</script>

{#if checking}
	<div class="setup-check">
		<div class="spinner"></div>
		<p>Verificando configuración del sistema...</p>
	</div>
{:else}
	{@render children()}
{/if}

<style>
	.setup-check {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		gap: 1rem;
		color: #64748b;
		font-family: system-ui, -apple-system, sans-serif;
	}
	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid #e2e8f0;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
