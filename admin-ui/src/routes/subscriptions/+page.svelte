<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import KpiCard from '$lib/components/KpiCard.svelte';
	import { getSubscriptions, getSubscriptionStats, isAuthenticated } from '$lib/api.js';

	let data = $state(null);
	let stats = $state(null);
	let loading = $state(true);
	let planFilter = $state('');
	let statusFilter = $state('');

	const planBadge = { free: 'badge-gray', starter: 'badge-info', pro: 'badge-purple', enterprise: 'badge-warning' };
	const statusBadge = { active: 'badge-success', trialing: 'badge-info', past_due: 'badge-warning', cancelled: 'badge-danger' };

	async function load() {
		loading = true;
		const params = new URLSearchParams();
		if (planFilter) params.set('plan', planFilter);
		if (statusFilter) params.set('status', statusFilter);
		[data, stats] = await Promise.all([
			getSubscriptions(params.toString()),
			getSubscriptionStats(),
		]);
		loading = false;
	}

	onMount(() => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		load();
	});
</script>

<AdminLayout>
	<h1 style="font-size: 30px; font-weight: 600; margin-bottom: var(--space-6)">Suscripciones</h1>

	{#if stats}
		<div class="kpi-grid">
			<KpiCard label="Activas" value={stats.active || 0} accent="success" />
			<KpiCard label="Trialing" value={stats.trialing || 0} accent="info" />
			<KpiCard label="Past Due" value={stats.past_due || 0} accent="warning" />
			<KpiCard label="Canceladas" value={stats.cancelled || 0} accent="primary" />
		</div>
	{/if}

	<div style="display:flex; gap: var(--space-3); margin-bottom: var(--space-4)">
		<select bind:value={planFilter} onchange={load}>
			<option value="">Todos los planes</option>
			<option value="free">Free</option>
			<option value="starter">Starter</option>
			<option value="pro">Pro</option>
			<option value="enterprise">Enterprise</option>
		</select>
		<select bind:value={statusFilter} onchange={load}>
			<option value="">Todos los estados</option>
			<option value="active">Active</option>
			<option value="trialing">Trialing</option>
			<option value="past_due">Past Due</option>
			<option value="cancelled">Cancelled</option>
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
							<th>Org ID</th>
							<th>Plan</th>
							<th>Estado</th>
							<th>Pasarela</th>
							<th>Creada</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as sub}
							<tr class:past-due={sub.status === 'past_due'}>
								<td class="mono text-sm">{sub.organization_id?.substring(0, 8)}...</td>
								<td><span class="badge {planBadge[sub.plan] || 'badge-gray'}">{sub.plan}</span></td>
								<td><span class="badge {statusBadge[sub.status] || 'badge-gray'}">{sub.status}</span></td>
								<td class="text-sm">{sub.gateway || '—'}</td>
								<td class="text-sm text-secondary">{new Date(sub.created_at).toLocaleDateString('es')}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="card" style="text-align:center">
			<p class="text-secondary">No hay suscripciones</p>
		</div>
	{/if}
</AdminLayout>

<style>
	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: var(--space-4);
		margin-bottom: var(--space-6);
	}
	tr.past-due td { background: rgba(217, 119, 6, 0.05); }
</style>
