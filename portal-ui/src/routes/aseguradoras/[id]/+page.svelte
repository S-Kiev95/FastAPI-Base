<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getInsurer, deleteInsurer, updateInsurer } from '$lib/api.js';

	let insurer = $state(null);
	let loading = $state(true);
	let error = $state('');

	let insurerId = $page.params.id;

	async function handleDelete() {
		if (!confirm('¿Borrar esta aseguradora? Esta acción no se puede deshacer.')) return;
		try {
			await deleteInsurer(insurerId);
			goto(`${base}/aseguradoras`);
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
			nombre: insurer.nombre || '',
			telefono: insurer.telefono || '',
			email: insurer.email || '',
			direccion: insurer.direccion || ''
		};
		editError = '';
		editModalOpen = true;
	}

	async function handleEditSubmit(e) {
		e.preventDefault();
		editLoading = true;
		editError = '';
		try {
			await updateInsurer(insurerId, { ...editForm });
			insurer = await getInsurer(insurerId);
			editModalOpen = false;
		} catch (err) {
			editError = err.message;
		} finally {
			editLoading = false;
		}
	}

	onMount(async () => {
		try {
			insurer = await getInsurer(insurerId);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});
</script>

<PortalLayout>
	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else if insurer}
		<div class="page-header">
			<h1>{insurer.nombre}</h1>
			<div style="display:flex; gap: var(--space-2)">
				<button class="btn btn-primary btn-sm" onclick={openEditModal}>Editar</button>
				<button class="btn btn-danger btn-sm" onclick={handleDelete}>Borrar</button>
				<a href="{base}/aseguradoras" class="btn btn-secondary">Volver</a>
			</div>
		</div>

		<div class="card" style="margin-bottom: var(--space-6)">
			<div class="detail-grid">
				<div class="detail-item">
					<span class="detail-label">Nombre</span>
					<span>{insurer.nombre}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">RUT</span>
					<span class="mono">{insurer.rut || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Telefono</span>
					<span>{insurer.telefono || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Email</span>
					<span>{insurer.email || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Direccion</span>
					<span>{insurer.direccion || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Sitio Web</span>
					<span>{insurer.sitio_web || '—'}</span>
				</div>
			</div>
		</div>

		{#if insurer.contactos}
			<h2 style="margin-bottom: var(--space-4)">Contactos</h2>
			<div class="card" style="margin-bottom: var(--space-6)">
				{#if Array.isArray(insurer.contactos) && insurer.contactos.length > 0}
					<div class="table-wrapper">
						<table>
							<thead>
								<tr>
									<th>Nombre</th>
									<th>Cargo</th>
									<th>Telefono</th>
									<th>Email</th>
								</tr>
							</thead>
							<tbody>
								{#each insurer.contactos as c}
									<tr>
										<td>{c.nombre || '—'}</td>
										<td>{c.cargo || '—'}</td>
										<td>{c.telefono || '—'}</td>
										<td>{c.email || '—'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else if typeof insurer.contactos === 'object'}
					<pre class="mono" style="white-space: pre-wrap; font-size: 13px;">{JSON.stringify(insurer.contactos, null, 2)}</pre>
				{/if}
			</div>
		{/if}

		{#if insurer.talleres && insurer.talleres.length > 0}
			<h2 style="margin-bottom: var(--space-4)">Talleres Asociados</h2>
			<div class="card" style="padding:0; overflow:hidden;">
				<table>
					<thead>
						<tr>
							<th>Nombre</th>
							<th>Direccion</th>
							<th>Telefono</th>
						</tr>
					</thead>
					<tbody>
						{#each insurer.talleres as t}
							<tr>
								<td>{t.nombre || '—'}</td>
								<td>{t.direccion || '—'}</td>
								<td>{t.telefono || '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</PortalLayout>

<Modal open={editModalOpen} title="Editar aseguradora" onClose={() => editModalOpen = false}>
	<form onsubmit={handleEditSubmit}>
		<div class="form-group"><label for="e-nombre">Nombre</label><input id="e-nombre" bind:value={editForm.nombre} required /></div>
		<div class="form-row">
			<div class="form-group"><label for="e-tel">Telefono</label><input id="e-tel" bind:value={editForm.telefono} /></div>
			<div class="form-group"><label for="e-email">Email</label><input id="e-email" type="email" bind:value={editForm.email} /></div>
		</div>
		<div class="form-group"><label for="e-dir">Direccion</label><input id="e-dir" bind:value={editForm.direccion} /></div>
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
