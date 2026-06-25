<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getPolicies } from '$lib/api.js';

	let policies = $state([]);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			policies = await getPolicies() || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Polizas</h1>
		<a href="{base}/polizas/nueva" class="btn btn-primary">+ Nueva Poliza</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if policies.length > 0}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>N. Poliza</th>
								<th>Tipo Seguro</th>
								<th>Cliente</th>
								<th>Vigente Hasta</th>
								<th>Prima Total</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each policies as p}
								<tr style="cursor:pointer" onclick={() => goto(`${base}/polizas/${p.id}`)}>
									<td class="mono">{p.numero_poliza}</td>
									<td>{p.tipo_seguro || '—'}</td>
									<td>{p.cliente_nombre || p.cliente_id || '—'}</td>
									<td>{p.vigente_hasta || '—'}</td>
									<td>{p.prima_total?.toLocaleString() ?? '—'}</td>
									<td><StatusBadge status={p.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="empty-state"><p>No hay polizas registradas.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>
