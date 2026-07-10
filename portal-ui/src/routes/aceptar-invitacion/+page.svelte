<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { acceptInvitation } from '$lib/api.js';

	let status = $state('loading'); // loading | ok | error
	let message = $state('');

	onMount(async () => {
		const token = $page.url.searchParams.get('token');
		if (!token) {
			status = 'error';
			message = 'Falta el token de invitación en el link.';
			return;
		}
		// Si no hay sesión, mandar a registro (o login) llevando el token
		const loggedIn = typeof localStorage !== 'undefined' && localStorage.getItem('portal_token');
		if (!loggedIn) {
			goto(`${base}/registro?invite=${encodeURIComponent(token)}`);
			return;
		}
		try {
			const res = await acceptInvitation(token);
			status = 'ok';
			message = res?.message || 'Te uniste a la organización correctamente.';
		} catch (err) {
			status = 'error';
			message = err.message || 'No se pudo aceptar la invitación.';
		}
	});
</script>

<div class="accept-page">
	<div class="card accept-card">
		<h1 style="margin-bottom: var(--space-4)">Invitación</h1>
		{#if status === 'loading'}
			<div class="loading"><div class="spinner"></div></div>
		{:else if status === 'ok'}
			<div class="alert alert-success">{message}</div>
			<a href="{base}/equipo" class="btn btn-primary" style="margin-top: var(--space-2)">Ir al portal</a>
		{:else}
			<div class="alert alert-danger">{message}</div>
			<a href="{base}/dashboard" class="btn btn-secondary" style="margin-top: var(--space-2)">Volver al inicio</a>
		{/if}
	</div>
</div>

<style>
	.accept-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: var(--color-surface-alt);
	}
	.accept-card {
		width: 100%;
		max-width: 440px;
		margin: var(--space-4);
	}
</style>
