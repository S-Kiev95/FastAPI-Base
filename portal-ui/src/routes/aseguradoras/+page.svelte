<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { getInsurers } from '$lib/api.js';

	let insurers = $state([]);
	let loading = $state(true);
	let error = $state('');

	const columns = [
		{ key: 'nombre', label: 'Nombre' },
		{ key: 'rut', label: 'RUT' },
		{ key: 'telefono', label: 'Telefono' },
		{ key: 'email', label: 'Email' },
		{
			key: 'activa',
			label: 'Estado',
			render: (val) => val !== false
				? '<span class="badge badge-success">Activa</span>'
				: '<span class="badge badge-gray">Inactiva</span>'
		},
	];

	onMount(async () => {
		try {
			insurers = await getInsurers() || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});

	function handleRowClick(row) {
		goto(`${base}/aseguradoras/${row.id}`);
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Aseguradoras</h1>
		<a href="{base}/aseguradoras/nueva" class="btn btn-primary">+ Nueva Aseguradora</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<DataTable {columns} data={insurers} onRowClick={handleRowClick} />
	{/if}
</PortalLayout>
