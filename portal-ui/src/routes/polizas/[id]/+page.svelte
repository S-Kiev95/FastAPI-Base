<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getPolicy, getPolicyInstallments, getPolicyClaims } from '$lib/api.js';

	let policy = $state(null);
	let installments = $state([]);
	let claims = $state([]);
	let loading = $state(true);
	let error = $state('');
	let activeTab = $state('detalle');

	let policyId = $page.params.id;

	onMount(async () => {
		try {
			const [p, inst, cl] = await Promise.all([
				getPolicy(policyId),
				getPolicyInstallments(policyId).catch(() => []),
				getPolicyClaims(policyId).catch(() => [])
			]);
			policy = p;
			installments = inst || [];
			claims = cl || [];
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
	{:else if policy}
		<div class="page-header">
			<h1>Poliza {policy.numero_poliza}</h1>
			<a href="{base}/polizas" class="btn btn-secondary">Volver</a>
		</div>

		<div class="tabs">
			<button class="tab" class:active={activeTab === 'detalle'} onclick={() => activeTab = 'detalle'}>Detalle</button>
			<button class="tab" class:active={activeTab === 'cuotas'} onclick={() => activeTab = 'cuotas'}>Cuotas ({installments.length})</button>
			<button class="tab" class:active={activeTab === 'siniestros'} onclick={() => activeTab = 'siniestros'}>Siniestros ({claims.length})</button>
		</div>

		{#if activeTab === 'detalle'}
			<div class="card">
				<div class="detail-grid">
					<div class="detail-item">
						<span class="detail-label">Numero de Poliza</span>
						<span class="mono">{policy.numero_poliza}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Tipo de Seguro</span>
						<span>{policy.tipo_seguro || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Estado</span>
						<StatusBadge status={policy.estado} />
					</div>
					<div class="detail-item">
						<span class="detail-label">Cliente</span>
						<span>{policy.cliente_nombre || policy.cliente_id || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Vehiculo</span>
						<span>{policy.vehiculo_id || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Aseguradora</span>
						<span>{policy.aseguradora_nombre || policy.aseguradora_id || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Vigente Desde</span>
						<span>{policy.vigente_desde || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Vigente Hasta</span>
						<span>{policy.vigente_hasta || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Prima Total</span>
						<span>{policy.prima_total?.toLocaleString() ?? '—'} {policy.moneda || ''}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Total Cuotas</span>
						<span>{policy.total_cuotas ?? '—'}</span>
					</div>
				</div>
			</div>
		{:else if activeTab === 'cuotas'}
			<div class="card" style="padding:0; overflow:hidden;">
				{#if installments.length > 0}
					<table>
						<thead>
							<tr>
								<th>N. Cuota</th>
								<th>Monto</th>
								<th>Vencimiento</th>
								<th>Estado</th>
								<th>Fecha Pago</th>
							</tr>
						</thead>
						<tbody>
							{#each installments as inst}
								<tr>
									<td>{inst.numero_cuota ?? inst.numero ?? '—'}</td>
									<td>{inst.monto?.toLocaleString() ?? '—'}</td>
									<td>{inst.fecha_vencimiento || '—'}</td>
									<td><StatusBadge status={inst.pagada ? 'pagada' : (inst.fecha_vencimiento && new Date(inst.fecha_vencimiento) < new Date() ? 'vencido' : 'pendiente')} /></td>
									<td>{inst.fecha_pago || '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>No hay cuotas registradas.</p></div>
				{/if}
			</div>
		{:else if activeTab === 'siniestros'}
			<div class="card" style="padding:0; overflow:hidden;">
				{#if claims.length > 0}
					<table>
						<thead>
							<tr>
								<th>N. Siniestro</th>
								<th>Fecha</th>
								<th>Descripcion</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each claims as cl}
								<tr style="cursor:pointer" onclick={() => goto(`${base}/siniestros/${cl.id}`)}>
									<td class="mono">{cl.numero_siniestro || cl.id}</td>
									<td>{cl.fecha_ocurrencia || '—'}</td>
									<td>{cl.descripcion?.substring(0, 60) || '—'}</td>
									<td><StatusBadge status={cl.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>No hay siniestros registrados.</p></div>
				{/if}
			</div>
		{/if}
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
