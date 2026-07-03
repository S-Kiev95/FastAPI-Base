<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { getClients, searchClients } from '$lib/api.js';

	let clients = $state([]);
	let loading = $state(true);
	let error = $state('');
	let searchQuery = $state('');
	let searchTimeout = $state(null);

	const columns = [
		{ key: 'nombre_completo', label: 'Nombre Completo' },
		{ key: 'documento_identidad', label: 'Documento' },
		{ key: 'telefono', label: 'Telefono' },
		{ key: 'email', label: 'Email' },
		{
			key: 'activo',
			label: 'Activo',
			render: (val) => val
				? '<span class="badge badge-success">Si</span>'
				: '<span class="badge badge-gray">No</span>'
		},
	];

	onMount(async () => {
		await loadClients();
	});

	async function loadClients() {
		loading = true;
		error = '';
		try {
			const data = await getClients();
			clients = (data || []).map(c => ({
				...c,
				nombre_completo: `${c.nombre || ''} ${c.apellido || ''}`.trim()
			}));
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function handleSearch(e) {
		const q = e.target.value;
		searchQuery = q;
		if (searchTimeout) clearTimeout(searchTimeout);
		searchTimeout = setTimeout(async () => {
			if (!q.trim()) {
				await loadClients();
				return;
			}
			loading = true;
			try {
				const data = await searchClients(q);
				clients = (data || []).map(c => ({
					...c,
					nombre_completo: `${c.nombre || ''} ${c.apellido || ''}`.trim()
				}));
			} catch (err) {
				error = err.message;
			} finally {
				loading = false;
			}
		}, 300);
	}

	function handleRowClick(row) {
		goto(`${base}/clientes/${row.id}`);
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Clientes</h1>
		<a href="{base}/clientes/nuevo" class="btn btn-primary">+ Nuevo Cliente</a>
	</div>

	<div style="margin-bottom: var(--space-4)">
		<input
			type="search"
			placeholder="Buscar clientes por nombre, documento, email…"
			value={searchQuery}
			oninput={handleSearch}
			style="width: 100%; max-width: 400px;"
		/>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<DataTable {columns} data={clients} onRowClick={handleRowClick} />
	{/if}
</PortalLayout>
