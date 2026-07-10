<script>
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/stores';

	let { children } = $props();
	let checking = $state(true);

	onMount(() => {
		const currentPath = $page.url.pathname;

		// Rutas públicas (sin sesión): login, registro, aceptar invitación
		if (currentPath.includes('/login') || currentPath.includes('/registro') || currentPath.includes('/aceptar-invitacion')) {
			checking = false;
			return;
		}

		const token = localStorage.getItem('portal_token');
		if (!token) {
			checking = false;
			goto(`${base}/login`);
			return;
		}

		checking = false;
	});
</script>

{#if checking}
	<div class="auth-check">
		<div class="spinner"></div>
		<p>Verificando sesion…</p>
	</div>
{:else}
	{@render children()}
{/if}

<style>
	.auth-check {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		gap: 1rem;
		color: #64748b;
		font-family: system-ui, -apple-system, sans-serif;
	}
</style>
