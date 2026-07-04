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
			goto(`${base}/`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<div class="login-page">
	<div class="login-card card">
		<h1 class="login-title">Admin Panel</h1>
		<p class="text-secondary" style="margin-bottom: var(--space-6)">Seguros BK — Iniciar sesión</p>

		{#if error}
			<div class="alert alert-danger">{error}</div>
		{/if}

		<form onsubmit={handleLogin}>
			<div class="form-group">
				<label for="email">Email</label>
				<input id="email" type="email" bind:value={email} required placeholder="admin@example.com" />
			</div>
			<div class="form-group">
				<label for="password">Contraseña</label>
				<input id="password" type="password" bind:value={password} required />
			</div>
			<button class="btn btn-primary" style="width:100%; margin-top: var(--space-4)" disabled={loading}>
				{loading ? 'Ingresando...' : 'Ingresar'}
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
	.form-group {
		margin-bottom: var(--space-4);
	}
	.form-group label {
		display: block;
		font-size: 13px;
		font-weight: 500;
		margin-bottom: var(--space-1);
		color: var(--color-text-secondary);
	}
	.form-group input {
		width: 100%;
	}
	.alert-danger {
		background: #FEE2E2;
		color: #991B1B;
		padding: var(--space-3);
		border-radius: var(--radius-md);
		font-size: 13px;
		margin-bottom: var(--space-4);
	}
</style>
