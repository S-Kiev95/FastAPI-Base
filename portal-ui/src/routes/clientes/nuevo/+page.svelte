<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createClient } from '$lib/api.js';

	let form = $state({
		nombre: '',
		apellido: '',
		documento_identidad: '',
		telefono: '',
		email: '',
		direccion: '',
		fecha_nacimiento: ''
	});
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			const data = { ...form };
			if (!data.fecha_nacimiento) delete data.fecha_nacimiento;
			await createClient(data);
			goto(`${base}/clientes`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nuevo Cliente</h1>
		<a href="{base}/clientes" class="btn btn-secondary">Cancelar</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	<div class="card">
		<form onsubmit={handleSubmit}>
			<div class="form-row">
				<div class="form-group">
					<label for="nombre">Nombre</label>
					<input id="nombre" type="text" bind:value={form.nombre} required />
				</div>
				<div class="form-group">
					<label for="apellido">Apellido</label>
					<input id="apellido" type="text" bind:value={form.apellido} required />
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="documento">Documento de Identidad</label>
					<input id="documento" type="text" bind:value={form.documento_identidad} required />
				</div>
				<div class="form-group">
					<label for="telefono">Telefono</label>
					<input id="telefono" type="tel" bind:value={form.telefono} />
				</div>
			</div>

			<div class="form-group">
				<label for="email">Email</label>
				<input id="email" type="email" bind:value={form.email} />
			</div>

			<div class="form-group">
				<label for="direccion">Direccion</label>
				<input id="direccion" type="text" bind:value={form.direccion} />
			</div>

			<div class="form-group">
				<label for="fecha_nac">Fecha de Nacimiento</label>
				<input id="fecha_nac" type="date" bind:value={form.fecha_nacimiento} />
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando…' : 'Guardar Cliente'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
