<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getClient, getClientVehicles, getClientPolicies } from '$lib/api.js';

	let client = $state(null);
	let vehicles = $state([]);
	let policies = $state([]);
	let loading = $state(true);
	let error = $state('');
	let activeTab = $state('datos');

	let clientId = $page.params.id;

	onMount(async () => {
		try {
			const [c, v, p] = await Promise.all([
				getClient(clientId),
				getClientVehicles(clientId).catch(() => []),
				getClientPolicies(clientId).catch(() => [])
			]);
			client = c;
			vehicles = v || [];
			policies = p || [];
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
	{:else if client}
		<div class="page-header">
			<h1>{client.nombre} {client.apellido}</h1>
			<a href="{base}/clientes" class="btn btn-secondary">Volver</a>
		</div>

		<div class="tabs">
			<button class="tab" class:active={activeTab === 'datos'} onclick={() => activeTab = 'datos'}>Datos</button>
			<button class="tab" class:active={activeTab === 'vehiculos'} onclick={() => activeTab = 'vehiculos'}>Vehiculos ({vehicles.length})</button>
			<button class="tab" class:active={activeTab === 'polizas'} onclick={() => activeTab = 'polizas'}>Polizas ({policies.length})</button>
		</div>

		{#if activeTab === 'datos'}
			<div class="card">
				<div class="detail-grid">
					<div class="detail-item">
						<span class="detail-label">Nombre</span>
						<span>{client.nombre} {client.apellido}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Documento</span>
						<span class="mono">{client.documento_identidad || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Telefono</span>
						<span>{client.telefono || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Email</span>
						<span>{client.email || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Direccion</span>
						<span>{client.direccion || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Fecha de Nacimiento</span>
						<span>{client.fecha_nacimiento || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Estado</span>
						<StatusBadge status={client.activo ? 'activo' : 'inactivo'} />
					</div>
				</div>
			</div>
		{:else if activeTab === 'vehiculos'}
			<div class="card" style="padding:0; overflow:hidden;">
				{#if vehicles.length > 0}
					<table>
						<thead>
							<tr>
								<th>Marca</th>
								<th>Modelo</th>
								<th>Anio</th>
								<th>Patente</th>
								<th>Chasis</th>
							</tr>
						</thead>
						<tbody>
							{#each vehicles as v}
								<tr>
									<td>{v.marca || '—'}</td>
									<td>{v.modelo || '—'}</td>
									<td>{v.anio || '—'}</td>
									<td class="mono">{v.patente || '—'}</td>
									<td class="mono">{v.numero_chasis || '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>Este cliente no tiene vehiculos registrados.</p></div>
				{/if}
			</div>
		{:else if activeTab === 'polizas'}
			<div class="card" style="padding:0; overflow:hidden;">
				{#if policies.length > 0}
					<table>
						<thead>
							<tr>
								<th>N. Poliza</th>
								<th>Tipo</th>
								<th>Vigente Hasta</th>
								<th>Prima Total</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each policies as p}
								<tr style="cursor:pointer" onclick={() => window.location.href = `${base}/polizas/${p.id}`}>
									<td class="mono">{p.numero_poliza}</td>
									<td>{p.tipo_seguro}</td>
									<td>{p.vigente_hasta}</td>
									<td>{p.prima_total?.toLocaleString() ?? '—'}</td>
									<td><StatusBadge status={p.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>Este cliente no tiene polizas.</p></div>
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
