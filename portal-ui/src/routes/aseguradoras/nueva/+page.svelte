<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createInsurer } from '$lib/api.js';

	let form = $state({ nombre: '', telefono: '', email: '', direccion: '' });
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			await createInsurer({ ...form });
			goto(`${base}/aseguradoras`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nueva Aseguradora</h1>
		<a href="{base}/aseguradoras" class="btn btn-secondary">Cancelar</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	<div class="card">
		<form onsubmit={handleSubmit}>
			<div class="form-group">
				<label for="nombre">Nombre</label>
				<input id="nombre" type="text" bind:value={form.nombre} required />
			</div>
			<div class="form-row">
				<div class="form-group">
					<label for="telefono">Telefono</label>
					<input id="telefono" type="text" bind:value={form.telefono} />
				</div>
				<div class="form-group">
					<label for="email">Email</label>
					<input id="email" type="email" bind:value={form.email} />
				</div>
			</div>
			<div class="form-group">
				<label for="direccion">Direccion</label>
				<input id="direccion" type="text" bind:value={form.direccion} />
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando…' : 'Crear Aseguradora'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
