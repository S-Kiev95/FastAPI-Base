<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { login } from '$lib/api.js';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin(e) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await login(email, password);
			goto(`${base}/dashboard`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<div class="login-page">
	<div class="login-card card">
		<h1 class="login-title">Portal de Seguros</h1>
		<p class="text-secondary" style="margin-bottom: var(--space-6)">Seguros BK — Iniciar sesion</p>

		{#if error}
			<div class="alert alert-danger">{error}</div>
		{/if}

		<form onsubmit={handleLogin}>
			<div class="form-group">
				<label for="email">Email</label>
				<input id="email" name="email" type="email" autocomplete="username" spellcheck="false" bind:value={email} required placeholder="usuario@ejemplo.com" />
			</div>
			<div class="form-group">
				<label for="password">Contrasena</label>
				<input id="password" name="password" type="password" autocomplete="current-password" bind:value={password} required />
			</div>
			<button class="btn btn-primary" style="width:100%; margin-top: var(--space-4)" disabled={loading}>
				{loading ? 'Ingresando…' : 'Ingresar'}
			</button>
		</form>
	</div>
</div>

<style>
	.login-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: var(--color-surface-alt);
	}
	.login-card {
		width: 100%;
		max-width: 400px;
		margin: var(--space-4);
	}
	.login-title {
		font-size: 24px;
		font-weight: 700;
		margin-bottom: var(--space-1);
	}
</style>
