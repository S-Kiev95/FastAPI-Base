<script>
	import { onMount } from 'svelte';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { getWorkshops } from '$lib/api.js';

	let workshops = $state([]);
	let loading = $state(true);
	let error = $state('');
	let departmentFilter = $state('');

	const columns = [
		{ key: 'nombre', label: 'Nombre' },
		{ key: 'direccion', label: 'Direccion' },
		{ key: 'departamento', label: 'Departamento' },
		{ key: 'telefono', label: 'Telefono' },
		{ key: 'especialidad', label: 'Especialidad' },
	];

	onMount(async () => {
		await loadWorkshops();
	});

	async function loadWorkshops() {
		loading = true;
		error = '';
		try {
			const params = {};
			if (departmentFilter) params.departamento = departmentFilter;
			workshops = await getWorkshops(params) || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	let departments = $state([]);
	$effect(() => {
		const depts = [...new Set((workshops || []).map(w => w.departamento).filter(Boolean))].sort();
		departments = depts;
	});

	let filteredWorkshops = $state([]);
	$effect(() => {
		if (!departmentFilter) {
			filteredWorkshops = workshops;
		} else {
			filteredWorkshops = workshops.filter(w => w.departamento === departmentFilter);
		}
	});

	function handleFilterChange() {
		// The $effect will handle filtering reactively
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Talleres</h1>
	</div>

	<div style="margin-bottom: var(--space-4); display: flex; gap: var(--space-3); align-items: center;">
		<label class="text-sm text-secondary" for="dept-filter">Filtrar por departamento:</label>
		<select id="dept-filter" bind:value={departmentFilter} onchange={handleFilterChange}>
			<option value="">Todos</option>
			{#each departments as dept}
				<option value={dept}>{dept}</option>
			{/each}
		</select>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<DataTable columns={columns} data={filteredWorkshops} />
	{/if}
</PortalLayout>
