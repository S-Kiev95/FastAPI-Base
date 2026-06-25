<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getClaims } from '$lib/api.js';

	let claims = $state([]);
	let loading = $state(true);
	let error = $state('');
	let statusFilter = $state('');

	const statusOptions = [
		{ value: '', label: 'Todos' },
		{ value: 'abierto', label: 'Abierto' },
		{ value: 'en_tramite', label: 'En Tramite' },
		{ value: 'liquidado', label: 'Liquidado' },
		{ value: 'rechazado', label: 'Rechazado' },
	];

	onMount(async () => {
		await loadClaims();
	});

	async function loadClaims() {
		loading = true;
		error = '';
		try {
			const params = {};
			if (statusFilter) params.estado = statusFilter;
			claims = await getClaims(params) || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function handleFilterChange() {
		loadClaims();
	}

	let filteredClaims = $state([]);
	$effect(() => {
		if (!statusFilter) {
			filteredClaims = claims;
		} else {
			filteredClaims = claims.filter(c => c.estado === statusFilter);
		}
	});
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Siniestros</h1>
		<a href="{base}/siniestros/nuevo" class="btn btn-primary">+ Nuevo Siniestro</a>
	</div>

	<div style="margin-bottom: var(--space-4); display: flex; gap: var(--space-3); align-items: center;">
		<label class="text-sm text-secondary" for="status-filter">Filtrar por estado:</label>
		<select id="status-filter" bind:value={statusFilter} onchange={handleFilterChange}>
			{#each statusOptions as opt}
				<option value={opt.value}>{opt.label}</option>
			{/each}
		</select>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if filteredClaims.length > 0}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>N. Siniestro</th>
								<th>Poliza</th>
								<th>Fecha</th>
								<th>Descripcion</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each filteredClaims as claim}
								<tr style="cursor:pointer" onclick={() => goto(`${base}/siniestros/${claim.id}`)}>
									<td class="mono">{claim.numero_siniestro || claim.id}</td>
									<td class="mono">{claim.poliza_numero || claim.poliza_id || '—'}</td>
									<td>{claim.fecha_siniestro || '—'}</td>
									<td>{claim.descripcion?.substring(0, 80) || '—'}</td>
									<td><StatusBadge status={claim.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="empty-state"><p>No hay siniestros registrados.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>
