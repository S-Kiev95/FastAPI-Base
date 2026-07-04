<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import { getOrganizations, toggleOrgActive, isAuthenticated } from '$lib/api.js';

	let data = $state(null);
	let loading = $state(true);
	let search = $state('');
	let planFilter = $state('');

	const planBadge = { free: 'badge-gray', starter: 'badge-info', pro: 'badge-purple', enterprise: 'badge-warning' };

	async function load() {
		loading = true;
		const params = new URLSearchParams();
		if (search) params.set('search', search);
		if (planFilter) params.set('plan', planFilter);
		data = await getOrganizations(params.toString());
		loading = false;
	}

	async function toggle(id, current) {
		await toggleOrgActive(id, !current);
		await load();
	}

	onMount(() => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		load();
	});
</script>

<AdminLayout>
	<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: var(--space-6)">
		<h1 style="font-size: 30px; font-weight: 600">Organizaciones</h1>
		<span class="badge badge-gray">{data?.total ?? 0} total</span>
	</div>

	<div style="display:flex; gap: var(--space-3); margin-bottom: var(--space-4)">
		<input placeholder="Buscar..." bind:value={search} onkeyup={(e) => e.key === 'Enter' && load()} style="flex:1" />
		<select bind:value={planFilter} onchange={load}>
			<option value="">Todos los planes</option>
			<option value="free">Free</option>
			<option value="starter">Starter</option>
			<option value="pro">Pro</option>
			<option value="enterprise">Enterprise</option>
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
							<th>Nombre</th>
							<th>Plan</th>
							<th>Estado</th>
							<th>Creada</th>
							<th>Acciones</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as org}
							<tr>
								<td>
									<div>{org.name}</div>
									<div class="mono text-secondary text-xs">{org.slug}</div>
								</td>
								<td><span class="badge {planBadge[org.plan] || 'badge-gray'}">{org.plan}</span></td>
								<td>
									{#if org.is_active}
										<span class="badge badge-success">Activa</span>
									{:else}
										<span class="badge badge-danger">Inactiva</span>
									{/if}
								</td>
								<td class="text-sm text-secondary">{new Date(org.created_at).toLocaleDateString('es')}</td>
								<td>
									<button class="btn btn-ghost text-sm" onclick={() => toggle(org.id, org.is_active)}>
										{org.is_active ? 'Desactivar' : 'Activar'}
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="card" style="text-align:center">
			<p class="text-secondary">No hay organizaciones</p>
		</div>
	{/if}
</AdminLayout>
