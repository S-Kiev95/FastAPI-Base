<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import { getPayments, isAuthenticated } from '$lib/api.js';

	let data = $state(null);
	let loading = $state(true);
	let statusFilter = $state('');

	const statusBadge = { succeeded: 'badge-success', failed: 'badge-danger', pending: 'badge-warning', refunded: 'badge-info' };

	async function load() {
		loading = true;
		const params = new URLSearchParams();
		if (statusFilter) params.set('status', statusFilter);
		data = await getPayments(params.toString());
		loading = false;
	}

	onMount(() => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		load();
	});
</script>

<AdminLayout>
	<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: var(--space-6)">
		<h1 style="font-size: 30px; font-weight: 600">Pagos</h1>
		<span class="badge badge-gray">{data?.total ?? 0} total</span>
	</div>

	<div style="margin-bottom: var(--space-4)">
		<select bind:value={statusFilter} onchange={load}>
			<option value="">Todos</option>
			<option value="succeeded">Succeeded</option>
			<option value="failed">Failed</option>
			<option value="pending">Pending</option>
			<option value="refunded">Refunded</option>
		</select>
	</div>

	{#if loading}
		<p class="text-secondary">Cargando...</p>
	{:else if data?.items?.length}
		<div class="card" style="padding:0; overflow:hidden">
			<div class="table-wrapper">
				<table>
					<thead>
						<tr>
							<th>ID</th>
							<th>Org ID</th>
							<th>Monto</th>
							<th>Estado</th>
							<th>Pasarela</th>
							<th>Descripción</th>
							<th>Fecha</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as payment}
							<tr>
								<td class="mono text-sm">{payment.id?.substring(0, 8)}...</td>
								<td class="mono text-sm">{payment.organization_id?.substring(0, 8)}...</td>
								<td style="font-variant-numeric: tabular-nums; font-weight:600">${(payment.amount / 100).toFixed(2)}</td>
								<td><span class="badge {statusBadge[payment.status] || 'badge-gray'}">{payment.status}</span></td>
								<td class="text-sm">{payment.gateway}</td>
								<td class="text-sm text-secondary">{payment.description || '—'}</td>
								<td class="text-sm text-secondary">{new Date(payment.created_at).toLocaleDateString('es')}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="card" style="text-align:center">
			<p class="text-secondary">No hay pagos registrados</p>
		</div>
	{/if}
</AdminLayout>
