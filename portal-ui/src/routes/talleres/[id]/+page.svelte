<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getWorkshop, updateWorkshop, deleteWorkshop } from '$lib/api.js';

	let workshop = $state(null);
	let loading = $state(true);
	let error = $state('');

	let workshopId = $page.params.id;

	onMount(async () => {
		try {
			workshop = await getWorkshop(workshopId);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});

	async function handleDelete() {
		if (!confirm('¿Borrar este taller? Esta acción no se puede deshacer.')) return;
		try {
			await deleteWorkshop(workshopId);
			goto(`${base}/talleres`);
		} catch (err) {
			error = err.message;
		}
	}

	let editModalOpen = $state(false);
	let editForm = $state({});
	let editLoading = $state(false);
	let editError = $state('');

	function openEditModal() {
		editForm = {
			nombre: workshop.nombre || '',
			departamento: workshop.departamento || '',
			ciudad: workshop.ciudad || '',
			especialidad: workshop.especialidad || 'general',
			telefono: workshop.telefono || '',
			direccion: workshop.direccion || '',
			marcas_atendidas: workshop.marcas_atendidas || '',
			activo: workshop.activo
		};
		editError = '';
		editModalOpen = true;
	}

	async function handleEditSubmit(e) {
		e.preventDefault();
		editLoading = true;
		editError = '';
		try {
			await updateWorkshop(workshopId, { ...editForm });
			workshop = await getWorkshop(workshopId);
			editModalOpen = false;
		} catch (err) {
			editError = err.message;
		} finally {
			editLoading = false;
		}
	}
</script>

<PortalLayout>
	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else if workshop}
		<div class="page-header">
			<h1>{workshop.nombre}</h1>
			<div style="display:flex; gap: var(--space-2)">
				<button class="btn btn-primary btn-sm" onclick={openEditModal}>Editar</button>
				<button class="btn btn-danger btn-sm" onclick={handleDelete}>Borrar</button>
				<a href="{base}/talleres" class="btn btn-secondary">Volver</a>
			</div>
		</div>

		<div class="card">
			<div class="detail-grid">
				<div class="detail-item">
					<span class="detail-label">Nombre</span>
					<span>{workshop.nombre}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Departamento</span>
					<span>{workshop.departamento || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Ciudad</span>
					<span>{workshop.ciudad || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Especialidad</span>
					<span>{workshop.especialidad || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Telefono</span>
					<span>{workshop.telefono || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Direccion</span>
					<span>{workshop.direccion || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Marcas Atendidas</span>
					<span>{workshop.marcas_atendidas || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Estado</span>
					<StatusBadge status={workshop.activo ? 'activo' : 'inactivo'} />
				</div>
			</div>
		</div>
	{/if}
</PortalLayout>

<Modal open={editModalOpen} title="Editar taller" onClose={() => editModalOpen = false}>
	<form onsubmit={handleEditSubmit}>
		<div class="form-row">
			<div class="form-group"><label for="e-nombre">Nombre</label><input id="e-nombre" bind:value={editForm.nombre} required /></div>
			<div class="form-group"><label for="e-depto">Departamento</label><input id="e-depto" bind:value={editForm.departamento} required /></div>
		</div>
		<div class="form-row">
			<div class="form-group"><label for="e-ciudad">Ciudad</label><input id="e-ciudad" bind:value={editForm.ciudad} /></div>
			<div class="form-group">
				<label for="e-esp">Especialidad</label>
				<select id="e-esp" bind:value={editForm.especialidad}>
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
			<div class="form-group"><label for="e-tel">Telefono</label><input id="e-tel" bind:value={editForm.telefono} /></div>
			<div class="form-group"><label for="e-marcas">Marcas atendidas</label><input id="e-marcas" bind:value={editForm.marcas_atendidas} /></div>
		</div>
		<div class="form-group"><label for="e-dir">Direccion</label><input id="e-dir" bind:value={editForm.direccion} /></div>
		<div class="form-group">
			<label for="e-activo" style="display:flex; align-items:center; gap:8px; cursor:pointer">
				<input id="e-activo" type="checkbox" bind:checked={editForm.activo} style="width:auto; height:auto; margin:0" /> Activo
			</label>
		</div>
		{#if editError}<div class="alert alert-danger">{editError}</div>{/if}
		<div style="display:flex; gap: var(--space-3); justify-content:flex-end; margin-top: var(--space-4)">
			<button type="button" class="btn btn-ghost" onclick={() => editModalOpen = false}>Cancelar</button>
			<button type="submit" class="btn btn-primary" disabled={editLoading}>{editLoading ? 'Guardando…' : 'Guardar'}</button>
		</div>
	</form>
</Modal>

<style>
	.detail-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: var(--space-4);
	}
	.detail-item {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.detail-label {
		font-size: 12px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-text-secondary);
	}
</style>
