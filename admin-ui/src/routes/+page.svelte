<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import KpiCard from '$lib/components/KpiCard.svelte';
	import { getDashboard, isAuthenticated } from '$lib/api.js';

	let stats = $state(null);
	let loading = $state(true);

	onMount(async () => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		try {
			stats = await getDashboard();
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	});
</script>

<AdminLayout>
	<h1 style="font-size: 30px; font-weight: 600; margin-bottom: var(--space-6)">Dashboard</h1>

	{#if loading}
		<p class="text-secondary">Cargando...</p>
	{:else if stats}
		<div class="kpi-grid">
			<KpiCard label="Organizaciones" value={stats.total_organizations} accent="primary" />
			<KpiCard label="Usuarios" value={stats.total_users} accent="info" />
			<KpiCard label="MRR" value={stats.mrr} format="currency" accent="success" />
			<KpiCard label="Suscripciones activas" value={stats.active_subscriptions} accent="warning" />
		</div>

		<div class="stats-row">
			<div class="card">
				<h2 style="font-size: 16px; font-weight: 600; margin-bottom: var(--space-4)">Resumen</h2>
				<div class="stat-line">
					<span class="text-secondary">Orgs activas</span>
					<span>{stats.active_organizations}</span>
				</div>
				<div class="stat-line">
					<span class="text-secondary">Nuevas (30d)</span>
					<span>{stats.new_organizations_30d}</span>
				</div>
			</div>
		</div>
	{/if}
</AdminLayout>

<style>
	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: var(--space-4);
		margin-bottom: var(--space-8);
	}
	.stats-row {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: var(--space-4);
	}
	.stat-line {
		display: flex;
		justify-content: space-between;
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--color-border);
		font-size: 14px;
	}
</style>
