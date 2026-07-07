<script>
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getMyTasks, completeTask, deleteTask, updateTask } from '$lib/api.js';

	let tasks = $state([]);
	let loading = $state(true);
	let error = $state('');
	let statusFilter = $state('');
	let priorityFilter = $state('');

	const statusOptions = [
		{ value: '', label: 'Todos' },
		{ value: 'pendiente', label: 'Pendiente' },
		{ value: 'en_progreso', label: 'En progreso' },
		{ value: 'completada', label: 'Completada' },
	];

	const priorityOptions = [
		{ value: '', label: 'Todas' },
		{ value: 'alta', label: 'Alta' },
		{ value: 'media', label: 'Media' },
		{ value: 'baja', label: 'Baja' },
	];

	onMount(async () => {
		await loadTasks();
	});

	async function loadTasks() {
		loading = true;
		error = '';
		try {
			tasks = await getMyTasks() || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	let filteredTasks = $state([]);
	$effect(() => {
		let result = tasks || [];
		if (statusFilter) {
			result = result.filter(t => t.estado === statusFilter);
		}
		if (priorityFilter) {
			result = result.filter(t => t.prioridad === priorityFilter);
		}
		filteredTasks = result;
	});

	async function handleComplete(taskId) {
		try {
			await completeTask(taskId);
			tasks = tasks.map(t =>
				t.id === taskId ? { ...t, estado: 'completada' } : t
			);
		} catch (err) {
			error = err.message;
		}
	}

	async function handleDelete(taskId) {
		if (!confirm('¿Borrar esta tarea? Esta acción no se puede deshacer.')) return;
		try {
			await deleteTask(taskId);
			tasks = tasks.filter(t => t.id !== taskId);
		} catch (err) {
			error = err.message;
		}
	}

	let editModalOpen = $state(false);
	let editId = $state(null);
	let editForm = $state({});
	let editLoading = $state(false);
	let editError = $state('');

	function openEditModal(task) {
		editId = task.id;
		editForm = {
			titulo: task.titulo || '',
			descripcion: task.descripcion || '',
			prioridad: task.prioridad || 'media',
			estado: task.estado || 'pendiente',
			fecha_vencimiento: task.fecha_vencimiento || ''
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
			if (!data.fecha_vencimiento) delete data.fecha_vencimiento;
			const updated = await updateTask(editId, data);
			tasks = tasks.map(t => (t.id === editId ? { ...t, ...updated } : t));
			editModalOpen = false;
		} catch (err) {
			editError = err.message;
		} finally {
			editLoading = false;
		}
	}

	function priorityBadge(priority) {
		const map = { alta: 'badge-danger', media: 'badge-warning', baja: 'badge-info' };
		return map[priority] || 'badge-gray';
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Mis Tareas</h1>
		<a href="{base}/tareas/nueva" class="btn btn-primary">+ Nueva Tarea</a>
	</div>

	<div style="margin-bottom: var(--space-4); display: flex; gap: var(--space-4); align-items: center; flex-wrap: wrap;">
		<div style="display: flex; gap: var(--space-2); align-items: center;">
			<label class="text-sm text-secondary" for="status-filter">Estado:</label>
			<select id="status-filter" bind:value={statusFilter}>
				{#each statusOptions as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		</div>
		<div style="display: flex; gap: var(--space-2); align-items: center;">
			<label class="text-sm text-secondary" for="priority-filter">Prioridad:</label>
			<select id="priority-filter" bind:value={priorityFilter}>
				{#each priorityOptions as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		</div>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if filteredTasks.length > 0}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>Titulo</th>
								<th>Prioridad</th>
								<th>Fecha Limite</th>
								<th>Estado</th>
								<th>Acciones</th>
							</tr>
						</thead>
						<tbody>
							{#each filteredTasks as task}
								<tr>
									<td>
										<div>{task.titulo || task.descripcion?.substring(0, 60) || '—'}</div>
										{#if task.descripcion && task.titulo}
											<div class="text-xs text-secondary">{task.descripcion.substring(0, 80)}</div>
										{/if}
									</td>
									<td><span class="badge {priorityBadge(task.prioridad)}">{task.prioridad || '—'}</span></td>
									<td>{task.fecha_vencimiento || '—'}</td>
									<td><StatusBadge status={task.estado} /></td>
									<td>
										<div style="display:flex; gap: var(--space-2); align-items:center;">
											{#if task.estado !== 'completada'}
												<button class="btn btn-success btn-sm" onclick={() => handleComplete(task.id)}>
													Completar
												</button>
											{:else}
												<span class="text-secondary text-sm">Completada</span>
											{/if}
											<button class="btn btn-secondary btn-sm" onclick={() => openEditModal(task)}>Editar</button>
											<button class="btn btn-danger btn-sm" onclick={() => handleDelete(task.id)}>Borrar</button>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="empty-state"><p>No hay tareas.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>

<Modal open={editModalOpen} title="Editar tarea" onClose={() => editModalOpen = false}>
	<form onsubmit={handleEditSubmit}>
		<div class="form-group"><label for="e-titulo">Titulo</label><input id="e-titulo" bind:value={editForm.titulo} required /></div>
		<div class="form-row">
			<div class="form-group">
				<label for="e-prioridad">Prioridad</label>
				<select id="e-prioridad" bind:value={editForm.prioridad}>
					<option value="alta">Alta</option>
					<option value="media">Media</option>
					<option value="baja">Baja</option>
				</select>
			</div>
			<div class="form-group">
				<label for="e-estado">Estado</label>
				<select id="e-estado" bind:value={editForm.estado}>
					<option value="pendiente">Pendiente</option>
					<option value="en_progreso">En progreso</option>
					<option value="completada">Completada</option>
					<option value="cancelada">Cancelada</option>
				</select>
			</div>
		</div>
		<div class="form-group"><label for="e-fecha">Fecha de Vencimiento</label><input id="e-fecha" type="date" bind:value={editForm.fecha_vencimiento} /></div>
		<div class="form-group"><label for="e-desc">Descripcion</label><textarea id="e-desc" bind:value={editForm.descripcion} rows="3"></textarea></div>
		{#if editError}<div class="alert alert-danger">{editError}</div>{/if}
		<div style="display:flex; gap: var(--space-3); justify-content:flex-end; margin-top: var(--space-4)">
			<button type="button" class="btn btn-ghost" onclick={() => editModalOpen = false}>Cancelar</button>
			<button type="submit" class="btn btn-primary" disabled={editLoading}>{editLoading ? 'Guardando…' : 'Guardar'}</button>
		</div>
	</form>
</Modal>
