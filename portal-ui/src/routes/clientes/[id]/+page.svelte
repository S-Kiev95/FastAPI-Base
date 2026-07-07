<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getClient, getClientVehicles, getClientPolicies, createVehicle, deleteClient, deleteVehicle, updateClient } from '$lib/api.js';

	let client = $state(null);
	let vehicles = $state([]);
	let policies = $state([]);
	let loading = $state(true);
	let error = $state('');
	let activeTab = $state('datos');

	let clientId = $page.params.id;

	async function handleDelete() {
		if (!confirm('¿Borrar este cliente? Esta acción no se puede deshacer.')) return;
		try {
			await deleteClient(clientId);
			goto(`${base}/clientes`);
		} catch (err) {
			error = err.message;
		}
	}

	// Edición del cliente
	let editModalOpen = $state(false);
	let editForm = $state({});
	let editLoading = $state(false);
	let editError = $state('');

	function openEditModal() {
		editForm = {
			nombre: client.nombre || '',
			apellido: client.apellido || '',
			documento_identidad: client.documento_identidad || '',
			telefono: client.telefono || '',
			email: client.email || '',
			direccion: client.direccion || '',
			fecha_nacimiento: client.fecha_nacimiento || '',
			activo: client.activo
		};
		editError = '';
		editModalOpen = true;
	}

	async function handleEditSubmit(e) {
		e.preventDefault();
		editLoading = true;
		editError = '';
		try {
			const data = { ...editForm };
			if (!data.fecha_nacimiento) delete data.fecha_nacimiento;
			await updateClient(clientId, data);
			client = await getClient(clientId);
			editModalOpen = false;
		} catch (err) {
			editError = err.message;
		} finally {
			editLoading = false;
		}
	}

	onMount(async () => {
		try {
			const [c, v, p] = await Promise.all([
				getClient(clientId),
				getClientVehicles(clientId).catch(() => []),
				getClientPolicies(clientId).catch(() => [])
			]);
			client = c;
			vehicles = v || [];
			policies = p || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});

	// Alta de vehículo
	let vehModalOpen = $state(false);
	let vehForm = $state({ marca: '', modelo: '', anio: '', matricula: '', tipo: 'auto', color: '' });
	let vehLoading = $state(false);
	let vehError = $state('');

	function openVehModal() {
		vehForm = { marca: '', modelo: '', anio: '', matricula: '', tipo: 'auto', color: '' };
		vehError = '';
		vehModalOpen = true;
	}

	async function handleDeleteVehicle(id) {
		if (!confirm('¿Borrar este vehiculo? Esta acción no se puede deshacer.')) return;
		try {
			await deleteVehicle(id);
			vehicles = vehicles.filter(v => v.id !== id);
		} catch (err) {
			error = err.message;
		}
	}

	async function handleAddVehicle(e) {
		e.preventDefault();
		vehLoading = true;
		vehError = '';
		try {
			const data = {
				...vehForm,
				cliente_id: parseInt(clientId),
				anio: vehForm.anio ? parseInt(vehForm.anio) : null
			};
			await createVehicle(data);
			vehModalOpen = false;
			vehicles = (await getClientVehicles(clientId).catch(() => [])) || [];
		} catch (err) {
			vehError = err.message;
		} finally {
			vehLoading = false;
		}
	}
</script>

<PortalLayout>
	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else if client}
		<div class="page-header">
			<h1>{client.nombre} {client.apellido}</h1>
			<div style="display:flex; gap: var(--space-2)">
				<button class="btn btn-primary btn-sm" onclick={openEditModal}>Editar</button>
				<button class="btn btn-danger btn-sm" onclick={handleDelete}>Borrar</button>
				<a href="{base}/clientes" class="btn btn-secondary">Volver</a>
			</div>
		</div>

		<div class="tabs">
			<button class="tab" class:active={activeTab === 'datos'} onclick={() => activeTab = 'datos'}>Datos</button>
			<button class="tab" class:active={activeTab === 'vehiculos'} onclick={() => activeTab = 'vehiculos'}>Vehiculos ({vehicles.length})</button>
			<button class="tab" class:active={activeTab === 'polizas'} onclick={() => activeTab = 'polizas'}>Polizas ({policies.length})</button>
		</div>

		{#if activeTab === 'datos'}
			<div class="card">
				<div class="detail-grid">
					<div class="detail-item">
						<span class="detail-label">Nombre</span>
						<span>{client.nombre} {client.apellido}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Documento</span>
						<span class="mono">{client.documento_identidad || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Telefono</span>
						<span>{client.telefono || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Email</span>
						<span>{client.email || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Direccion</span>
						<span>{client.direccion || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Fecha de Nacimiento</span>
						<span>{client.fecha_nacimiento || '—'}</span>
					</div>
					<div class="detail-item">
						<span class="detail-label">Estado</span>
						<StatusBadge status={client.activo ? 'activo' : 'inactivo'} />
					</div>
				</div>
			</div>
		{:else if activeTab === 'vehiculos'}
			<div style="display:flex; justify-content:flex-end; margin-bottom: var(--space-4)">
				<button class="btn btn-primary btn-sm" onclick={openVehModal}>+ Agregar vehiculo</button>
			</div>
			<div class="card" style="padding:0; overflow:hidden;">
				{#if vehicles.length > 0}
					<table>
						<thead>
							<tr>
								<th>Marca</th>
								<th>Modelo</th>
								<th>Anio</th>
								<th>Patente</th>
								<th>Chasis</th>
								<th></th>
							</tr>
						</thead>
						<tbody>
							{#each vehicles as v}
								<tr>
									<td>{v.marca || '—'}</td>
									<td>{v.modelo || '—'}</td>
									<td>{v.anio || '—'}</td>
									<td class="mono">{v.matricula || '—'}</td>
									<td class="mono">{v.numero_chasis || '—'}</td>
									<td style="text-align:right"><button class="btn btn-danger btn-sm" onclick={() => handleDeleteVehicle(v.id)}>Borrar</button></td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>Este cliente no tiene vehiculos registrados.</p></div>
				{/if}
			</div>
		{:else if activeTab === 'polizas'}
			<div class="card" style="padding:0; overflow:hidden;">
				{#if policies.length > 0}
					<table>
						<thead>
							<tr>
								<th>N. Poliza</th>
								<th>Tipo</th>
								<th>Vigente Hasta</th>
								<th>Prima Total</th>
								<th>Estado</th>
							</tr>
						</thead>
						<tbody>
							{#each policies as p}
								<tr style="cursor:pointer" onclick={() => window.location.href = `${base}/polizas/${p.id}`}>
									<td class="mono">{p.numero_poliza}</td>
									<td>{p.tipo_seguro}</td>
									<td>{p.vigente_hasta}</td>
									<td>{p.prima_total?.toLocaleString() ?? '—'}</td>
									<td><StatusBadge status={p.estado} /></td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="empty-state"><p>Este cliente no tiene polizas.</p></div>
				{/if}
			</div>
		{/if}
	{/if}
</PortalLayout>

<Modal open={editModalOpen} title="Editar cliente" onClose={() => editModalOpen = false}>
	<form onsubmit={handleEditSubmit}>
		<div class="form-row">
			<div class="form-group"><label for="e-nombre">Nombre</label><input id="e-nombre" bind:value={editForm.nombre} required /></div>
			<div class="form-group"><label for="e-apellido">Apellido</label><input id="e-apellido" bind:value={editForm.apellido} required /></div>
		</div>
		<div class="form-row">
			<div class="form-group"><label for="e-doc">Documento</label><input id="e-doc" bind:value={editForm.documento_identidad} /></div>
			<div class="form-group"><label for="e-tel">Telefono</label><input id="e-tel" bind:value={editForm.telefono} /></div>
		</div>
		<div class="form-row">
			<div class="form-group"><label for="e-email">Email</label><input id="e-email" type="email" bind:value={editForm.email} /></div>
			<div class="form-group"><label for="e-nac">Fecha de Nacimiento</label><input id="e-nac" type="date" bind:value={editForm.fecha_nacimiento} /></div>
		</div>
		<div class="form-group"><label for="e-dir">Direccion</label><input id="e-dir" bind:value={editForm.direccion} /></div>
		<div class="form-group">
			<label for="e-activo" style="display:flex; align-items:center; gap:8px; cursor:pointer">
				<input id="e-activo" type="checkbox" bind:checked={editForm.activo} style="width:auto; height:auto; margin:0" /> Activo
			</label>
		</div>
		{#if editError}<div class="alert alert-danger">{editError}</div>{/if}
		<div style="display:flex; gap: var(--space-3); justify-content:flex-end; margin-top: var(--space-4)">
			<button type="button" class="btn btn-ghost" onclick={() => editModalOpen = false}>Cancelar</button>
			<button type="submit" class="btn btn-primary" disabled={editLoading}>{editLoading ? 'Guardando…' : 'Guardar'}</button>
		</div>
	</form>
</Modal>

<Modal open={vehModalOpen} title="Agregar vehiculo" onClose={() => vehModalOpen = false}>
	<form onsubmit={handleAddVehicle}>
		<div class="form-row">
			<div class="form-group"><label for="marca">Marca</label><input id="marca" bind:value={vehForm.marca} required /></div>
			<div class="form-group"><label for="modelo">Modelo</label><input id="modelo" bind:value={vehForm.modelo} /></div>
		</div>
		<div class="form-row">
			<div class="form-group"><label for="matricula">Matricula</label><input id="matricula" bind:value={vehForm.matricula} required /></div>
			<div class="form-group"><label for="anio">Anio</label><input id="anio" type="number" bind:value={vehForm.anio} /></div>
		</div>
		<div class="form-row">
			<div class="form-group">
				<label for="tipo">Tipo</label>
				<select id="tipo" bind:value={vehForm.tipo}>
					<option value="auto">Auto</option>
					<option value="moto">Moto</option>
					<option value="camion">Camion</option>
					<option value="utilitario">Utilitario</option>
					<option value="otro">Otro</option>
				</select>
			</div>
			<div class="form-group"><label for="color">Color</label><input id="color" bind:value={vehForm.color} /></div>
		</div>
		{#if vehError}<div class="alert alert-danger">{vehError}</div>{/if}
		<div style="display:flex; gap: var(--space-3); justify-content:flex-end; margin-top: var(--space-4)">
			<button type="button" class="btn btn-ghost" onclick={() => vehModalOpen = false}>Cancelar</button>
			<button type="submit" class="btn btn-primary" disabled={vehLoading}>{vehLoading ? 'Guardando…' : 'Agregar'}</button>
		</div>
	</form>
</Modal>

<style>
	.detail-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: var(--space-4);
	}
	.detail-item {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.detail-label {
		font-size: 12px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-text-secondary);
	}
</style>
