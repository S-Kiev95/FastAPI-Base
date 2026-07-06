<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getClaim, getClaimDocuments, markDocumentReceived, deleteClaim, updateClaim } from '$lib/api.js';

	let claim = $state(null);
	let documents = $state([]);
	let loading = $state(true);
	let error = $state('');

	let claimId = $page.params.id;

	async function handleDelete() {
		if (!confirm('¿Borrar este siniestro? Esta acción no se puede deshacer.')) return;
		try {
			await deleteClaim(claimId);
			goto(`${base}/siniestros`);
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
			estado: claim.estado || 'abierto',
			tipo_dano: claim.tipo_dano || 'dano_propio',
			fecha_ocurrencia: claim.fecha_ocurrencia || '',
			monto_reclamado: claim.monto_reclamado ?? '',
			monto_liquidado: claim.monto_liquidado ?? '',
			descripcion: claim.descripcion || ''
		};
		editError = '';
		editModalOpen = true;
	}

	async function handleEditSubmit(e) {
		e.preventDefault();
		editLoading = true;
		editError = '';
		try {
			const data = {
				...editForm,
				monto_reclamado: editForm.monto_reclamado === '' ? null : parseFloat(editForm.monto_reclamado),
				monto_liquidado: editForm.monto_liquidado === '' ? null : parseFloat(editForm.monto_liquidado)
			};
			await updateClaim(claimId, data);
			claim = await getClaim(claimId);
			editModalOpen = false;
		} catch (err) {
			editError = err.message;
		} finally {
			editLoading = false;
		}
	}

	onMount(async () => {
		try {
			const [c, docs] = await Promise.all([
				getClaim(claimId),
				getClaimDocuments(claimId).catch(() => [])
			]);
			claim = c;
			documents = docs || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});

	async function handleMarkReceived(docId) {
		try {
			await markDocumentReceived(claimId, docId);
			documents = documents.map(d =>
				d.id === docId ? { ...d, recibido: true } : d
			);
		} catch (err) {
			error = err.message;
		}
	}
</script>

<PortalLayout>
	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else if claim}
		<div class="page-header">
			<h1>Siniestro {claim.numero_siniestro || claim.id}</h1>
			<div style="display:flex; gap: var(--space-2)">
				<button class="btn btn-primary btn-sm" onclick={openEditModal}>Editar</button>
				<button class="btn btn-danger btn-sm" onclick={handleDelete}>Borrar</button>
				<a href="{base}/siniestros" class="btn btn-secondary">Volver</a>
			</div>
		</div>

		<div class="card" style="margin-bottom: var(--space-6)">
			<div class="detail-grid">
				<div class="detail-item">
					<span class="detail-label">Numero de Siniestro</span>
					<span class="mono">{claim.numero_siniestro || claim.id}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Poliza</span>
					<span class="mono">{claim.poliza_numero || claim.poliza_id || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Fecha del Siniestro</span>
					<span>{claim.fecha_ocurrencia || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Estado</span>
					<StatusBadge status={claim.estado} />
				</div>
				<div class="detail-item" style="grid-column: 1 / -1">
					<span class="detail-label">Descripcion</span>
					<span>{claim.descripcion || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Monto Reclamado</span>
					<span>{claim.monto_reclamado?.toLocaleString() ?? '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Monto Liquidado</span>
					<span>{claim.monto_liquidado?.toLocaleString() ?? '—'}</span>
				</div>
			</div>
		</div>

		<h2 style="margin-bottom: var(--space-4)">Documentos</h2>
		<div class="card" style="padding:0; overflow:hidden;">
			{#if documents.length > 0}
				<table>
					<thead>
						<tr>
							<th>Documento</th>
							<th>Tipo</th>
							<th>Recibido</th>
							<th>Acciones</th>
						</tr>
					</thead>
					<tbody>
						{#each documents as doc}
							<tr>
								<td>{doc.nombre || doc.tipo_documento || '—'}</td>
								<td>{doc.tipo_documento || '—'}</td>
								<td>
									{#if doc.recibido}
										<span class="badge badge-success">Si</span>
									{:else}
										<span class="badge badge-warning">Pendiente</span>
									{/if}
								</td>
								<td>
									{#if !doc.recibido}
										<button class="btn btn-sm btn-primary" onclick={() => handleMarkReceived(doc.id)}>
											Marcar recibido
										</button>
									{:else}
										<span class="text-secondary text-sm">Recibido</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<div class="empty-state"><p>No hay documentos asociados.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>

<Modal open={editModalOpen} title="Editar siniestro" onClose={() => editModalOpen = false}>
	<form onsubmit={handleEditSubmit}>
		<div class="form-row">
			<div class="form-group">
				<label for="e-estado">Estado</label>
				<select id="e-estado" bind:value={editForm.estado}>
					<option value="abierto">Abierto</option>
					<option value="en_tramite">En trámite</option>
					<option value="liquidado">Liquidado</option>
					<option value="rechazado">Rechazado</option>
					<option value="cerrado">Cerrado</option>
				</select>
			</div>
			<div class="form-group">
				<label for="e-tipo">Tipo de Daño</label>
				<select id="e-tipo" bind:value={editForm.tipo_dano}>
					<option value="dano_propio">Daño propio</option>
					<option value="dano_tercero">Daño a tercero</option>
					<option value="robo_total">Robo total</option>
					<option value="robo_parcial">Robo parcial</option>
					<option value="incendio">Incendio</option>
					<option value="otro">Otro</option>
				</select>
			</div>
		</div>
		<div class="form-row">
			<div class="form-group"><label for="e-fecha">Fecha de Ocurrencia</label><input id="e-fecha" type="date" bind:value={editForm.fecha_ocurrencia} /></div>
			<div class="form-group"><label for="e-reclamado">Monto Reclamado</label><input id="e-reclamado" type="number" step="0.01" bind:value={editForm.monto_reclamado} /></div>
		</div>
		<div class="form-group"><label for="e-liquidado">Monto Liquidado</label><input id="e-liquidado" type="number" step="0.01" bind:value={editForm.monto_liquidado} /></div>
		<div class="form-group"><label for="e-desc">Descripcion</label><textarea id="e-desc" bind:value={editForm.descripcion} rows="3"></textarea></div>
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
