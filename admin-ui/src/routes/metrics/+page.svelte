<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import { getMetrics, isAuthenticated } from '$lib/api.js';

	let metrics = $state(null);
	let loading = $state(true);

	const planLabels = { free: 'Free', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };
	const planColors = { free: '#94A3B8', starter: '#0891B2', pro: '#7C3AED', enterprise: '#D97706' };

	onMount(async () => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		try {
			metrics = await getMetrics();
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	});
</script>

<AdminLayout>
	<h1 style="font-size: 30px; font-weight: 600; margin-bottom: var(--space-6)">Métricas</h1>

	{#if loading}
		<p class="text-secondary">Cargando...</p>
	{:else if metrics}
		<div class="metrics-grid">
			<!-- Plan Distribution -->
			<div class="card">
				<h2 style="font-size: 16px; font-weight: 600; margin-bottom: var(--space-4)">Distribución por plan</h2>
				{#each Object.entries(metrics.plan_distribution) as [plan, count]}
					<div class="dist-row">
						<div class="dist-label">
							<span class="dist-dot" style="background: {planColors[plan] || '#94A3B8'}"></span>
							<span>{planLabels[plan] || plan}</span>
						</div>
						<span style="font-variant-numeric: tabular-nums; font-weight: 600">{count}</span>
					</div>
				{/each}
			</div>

			<!-- Subscription Stats -->
			<div class="card">
				<h2 style="font-size: 16px; font-weight: 600; margin-bottom: var(--space-4)">Estado de suscripciones</h2>
				{#each Object.entries(metrics.subscription_stats) as [status, count]}
					<div class="dist-row">
						<span style="text-transform: capitalize">{status.replace('_', ' ')}</span>
						<span style="font-variant-numeric: tabular-nums; font-weight: 600">{count}</span>
					</div>
				{/each}
			</div>

			<!-- General Stats -->
			<div class="card">
				<h2 style="font-size: 16px; font-weight: 600; margin-bottom: var(--space-4)">General</h2>
				<div class="dist-row">
					<span class="text-secondary">Total organizaciones</span>
					<span style="font-weight:600">{metrics.dashboard.total_organizations}</span>
				</div>
				<div class="dist-row">
					<span class="text-secondary">Total usuarios</span>
					<span style="font-weight:600">{metrics.dashboard.total_users}</span>
				</div>
				<div class="dist-row">
					<span class="text-secondary">MRR</span>
					<span style="font-weight:600">${metrics.dashboard.mrr}</span>
				</div>
				<div class="dist-row">
					<span class="text-secondary">Nuevas orgs (30d)</span>
					<span style="font-weight:600">{metrics.dashboard.new_organizations_30d}</span>
				</div>
			</div>
		</div>
	{/if}
</AdminLayout>

<style>
	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: var(--space-4);
	}
	.dist-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--space-2) 0;
		border-bottom: 1px solid var(--color-border);
		font-size: 14px;
	}
	.dist-label {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}
	.dist-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
</style>
