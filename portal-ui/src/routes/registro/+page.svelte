<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { register, login } from '$lib/api.js';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let orgName = $state('');
	let error = $state('');
	let loading = $state(false);

	let inviteToken = $derived($page.url.searchParams.get('invite') || '');

	async function handleSubmit(e) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await register(email, password, name, orgName || undefined);
			await login(email, password);
			if (inviteToken) {
				goto(`${base}/aceptar-invitacion?token=${encodeURIComponent(inviteToken)}`);
			} else {
				goto(`${base}/dashboard`);
			}
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<div class="auth-page">
	<div class="auth-card card">
		<h1 class="auth-title">Crear cuenta</h1>
		<p class="text-secondary" style="margin-bottom: var(--space-6)">Seguros BK — Portal</p>

		{#if inviteToken}
			<div class="alert alert-success" style="margin-bottom: var(--space-4)">Fuiste invitado a una organización. Creá tu cuenta para unirte.</div>
		{/if}
		{#if error}
			<div class="alert alert-danger">{error}</div>
		{/if}

		<form onsubmit={handleSubmit}>
			<div class="form-group">
				<label for="name">Nombre</label>
				<input id="name" name="name" type="text" autocomplete="name" bind:value={name} required />
			</div>
			<div class="form-group">
				<label for="email">Email</label>
				<input id="email" name="email" type="email" autocomplete="email" spellcheck="false" bind:value={email} required placeholder="usuario@ejemplo.com" />
			</div>
			<div class="form-group">
				<label for="password">Contraseña</label>
				<input id="password" name="password" type="password" autocomplete="new-password" bind:value={password} required />
			</div>
			<div class="form-group">
				<label for="org">Nombre de tu organización <span class="text-tertiary">(opcional)</span></label>
				<input id="org" name="organization" type="text" bind:value={orgName} placeholder="Se genera de tu email si lo dejás vacío" />
			</div>
			<button class="btn btn-primary" style="width:100%; margin-top: var(--space-4)" disabled={loading}>
				{loading ? 'Creando…' : 'Crear cuenta'}
			</button>
		</form>

		<p class="text-sm text-secondary" style="margin-top: var(--space-4); text-align:center">
			¿Ya tenés cuenta? <a href="{base}/login{inviteToken ? `?invite=${inviteToken}` : ''}">Iniciar sesión</a>
		</p>
	</div>
</div>

<style>
	.auth-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: var(--color-surface-alt);
	}
	.auth-card {
		width: 100%;
		max-width: 420px;
		margin: var(--space-4);
	}
	.auth-title {
		font-size: 24px;
		font-weight: 600;
		margin-bottom: var(--space-1);
	}
</style>
