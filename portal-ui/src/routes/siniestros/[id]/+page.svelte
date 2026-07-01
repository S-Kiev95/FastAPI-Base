<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getClaim, getClaimDocuments, markDocumentReceived } from '$lib/api.js';

	let claim = $state(null);
	let documents = $state([]);
	let loading = $state(true);
	let error = $state('');

	let claimId = $page.params.id;

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
			<a href="{base}/siniestros" class="btn btn-secondary">Volver</a>
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
