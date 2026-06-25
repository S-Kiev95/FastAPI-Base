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

		// No verificar auth en la página de login
		if (currentPath.includes('/login')) {
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
		<p>Verificando sesion...</p>
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
