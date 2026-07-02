<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createTask } from '$lib/api.js';

	let form = $state({
		titulo: '',
		descripcion: '',
		prioridad: 'media',
		fecha_vencimiento: ''
	});
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			const data = { ...form };
			if (!data.fecha_vencimiento) delete data.fecha_vencimiento;
			await createTask(data);
			goto(`${base}/tareas`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nueva Tarea</h1>
		<a href="{base}/tareas" class="btn btn-secondary">Cancelar</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	<div class="card">
		<form onsubmit={handleSubmit}>
			<div class="form-group">
				<label for="titulo">Titulo</label>
				<input id="titulo" type="text" bind:value={form.titulo} required />
			</div>
			<div class="form-row">
				<div class="form-group">
					<label for="prioridad">Prioridad</label>
					<select id="prioridad" bind:value={form.prioridad}>
						<option value="alta">Alta</option>
						<option value="media">Media</option>
						<option value="baja">Baja</option>
					</select>
				</div>
				<div class="form-group">
					<label for="fecha_vencimiento">Fecha de Vencimiento</label>
					<input id="fecha_vencimiento" type="date" bind:value={form.fecha_vencimiento} />
				</div>
			</div>
			<div class="form-group">
				<label for="descripcion">Descripcion</label>
				<textarea id="descripcion" bind:value={form.descripcion} rows="4"></textarea>
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando...' : 'Crear Tarea'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
