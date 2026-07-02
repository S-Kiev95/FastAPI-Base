<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createWorkshop } from '$lib/api.js';

	let form = $state({
		nombre: '',
		departamento: '',
		ciudad: '',
		especialidad: 'general',
		telefono: '',
		direccion: '',
		marcas_atendidas: ''
	});
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			await createWorkshop({ ...form });
			goto(`${base}/talleres`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nuevo Taller</h1>
		<a href="{base}/talleres" class="btn btn-secondary">Cancelar</a>
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
					<label for="departamento">Departamento</label>
					<input id="departamento" type="text" bind:value={form.departamento} required />
				</div>
			</div>
			<div class="form-row">
				<div class="form-group">
					<label for="ciudad">Ciudad</label>
					<input id="ciudad" type="text" bind:value={form.ciudad} />
				</div>
				<div class="form-group">
					<label for="especialidad">Especialidad</label>
					<select id="especialidad" bind:value={form.especialidad}>
						<option value="general">General</option>
						<option value="chapa_pintura">Chapa y pintura</option>
						<option value="mecanica">Mecanica</option>
						<option value="electricidad">Electricidad</option>
						<option value="cristales">Cristales</option>
						<option value="multimarca">Multimarca</option>
						<option value="oficial">Oficial</option>
					</select>
				</div>
			</div>
			<div class="form-row">
				<div class="form-group">
					<label for="telefono">Telefono</label>
					<input id="telefono" type="text" bind:value={form.telefono} />
				</div>
				<div class="form-group">
					<label for="marcas_atendidas">Marcas atendidas</label>
					<input id="marcas_atendidas" type="text" bind:value={form.marcas_atendidas} placeholder="Toyota, Fiat, ..." />
				</div>
			</div>
			<div class="form-group">
				<label for="direccion">Direccion</label>
				<input id="direccion" type="text" bind:value={form.direccion} />
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando...' : 'Crear Taller'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
