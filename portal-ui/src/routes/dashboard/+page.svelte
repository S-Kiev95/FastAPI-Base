<script>
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import KpiCard from '$lib/components/KpiCard.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getDashboard, getUpcomingExpirations } from '$lib/api.js';

	let dashboard = $state(null);
	let expirations = $state([]);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			const [dash, exp] = await Promise.all([
				getDashboard(),
				getUpcomingExpirations(30)
			]);
			dashboard = dash;
			expirations = exp || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Dashboard</h1>
	</div>

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else}
		<div class="kpi-grid">
			<KpiCard label="Total Clientes" value={dashboard?.total_clientes ?? 0} color="primary" />
			<KpiCard label="Polizas Activas" value={dashboard?.polizas_activas ?? 0} color="success" />
			<KpiCard label="Siniestros Abiertos" value={dashboard?.siniestros_abiertos ?? 0} color="danger" />
			<KpiCard label="Cuotas Vencidas" value={dashboard?.cuotas_vencidas ?? 0} color="warning" />
			<KpiCard label="Polizas por Vencer" value={dashboard?.polizas_por_vencer ?? 0} color="info" />
			<KpiCard label="Prima Total" value={dashboard?.prima_total ?? 0} color="primary" />
			<KpiCard label="Tareas Pendientes" value={dashboard?.tareas_pendientes ?? 0} color="warning" />
		</div>

		<div class="card" style="margin-top: var(--space-6)">
			<h2 style="margin-bottom: var(--space-4)">Polizas por vencer (30 dias)</h2>
			{#if expirations.length > 0}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>N. Poliza</th>
								<th>Cliente</th>
								<th>Tipo</th>
								<th>Vence</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each expirations as p}
								<tr style="cursor:pointer" onclick={() => window.location.href = `${base}/polizas/${p.id}`}>
									<td class="mono">{p.numero_poliza}</td>
									<td>{p.cliente_nombre || p.cliente_id}</td>
									<td>{p.tipo_seguro}</td>
									<td>{p.vigente_hasta}</td>
									<td><StatusBadge status={p.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="empty-state">
					<p>No hay polizas proximas a vencer.</p>
				</div>
			{/if}
		</div>
	{/if}
</PortalLayout>

<style>
	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: var(--space-4);
	}
</style>
