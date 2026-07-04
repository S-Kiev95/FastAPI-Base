<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import AdminLayout from '$lib/components/AdminLayout.svelte';
	import { getUsers, toggleUserActive, impersonateUser, isAuthenticated } from '$lib/api.js';

	let data = $state(null);
	let loading = $state(true);
	let search = $state('');

	async function load() {
		loading = true;
		const params = new URLSearchParams();
		if (search) params.set('search', search);
		data = await getUsers(params.toString());
		loading = false;
	}

	async function toggle(id, current) {
		await toggleUserActive(id, !current);
		await load();
	}

	async function impersonate(id) {
		if (!confirm('¿Iniciar sesión como este usuario?')) return;
		const result = await impersonateUser(id);
		alert(`Token generado para ${result.impersonated_user.email}.\nCopiá el token desde la consola.`);
		console.log('Impersonate token:', result.access_token);
	}

	onMount(() => {
		if (!isAuthenticated()) { goto(`${base}/login`); return; }
		load();
	});
</script>

<AdminLayout>
	<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: var(--space-6)">
		<h1 style="font-size: 30px; font-weight: 600">Usuarios</h1>
		<span class="badge badge-gray">{data?.total ?? 0} total</span>
	</div>

	<div style="margin-bottom: var(--space-4)">
		<input placeholder="Buscar por email o nombre..." bind:value={search} onkeyup={(e) => e.key === 'Enter' && load()} style="width:100%; max-width:400px" />
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
							<th>Nombre</th>
							<th>Email</th>
							<th>Proveedor</th>
							<th>Estado</th>
							<th>Acciones</th>
						</tr>
					</thead>
					<tbody>
						{#each data.items as user}
							<tr>
								<td class="mono">{user.id}</td>
								<td>{user.name || '—'}</td>
								<td>{user.email}</td>
								<td><span class="badge badge-gray">{user.provider}</span></td>
								<td>
									{#if user.is_active}
										<span class="badge badge-success">Activo</span>
									{:else}
										<span class="badge badge-danger">Inactivo</span>
									{/if}
								</td>
								<td style="display:flex; gap: var(--space-2)">
									<button class="btn btn-ghost text-sm" onclick={() => toggle(user.id, user.is_active)}>
										{user.is_active ? 'Desactivar' : 'Activar'}
									</button>
									<button class="btn btn-ghost text-sm" onclick={() => impersonate(user.id)}>
										Impersonar
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
			<p class="text-secondary">No hay usuarios</p>
		</div>
	{/if}
</AdminLayout>
