<script>
	import { onMount } from 'svelte';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getMyTasks, completeTask } from '$lib/api.js';

	let tasks = $state([]);
	let loading = $state(true);
	let error = $state('');
	let statusFilter = $state('');
	let priorityFilter = $state('');

	const statusOptions = [
		{ value: '', label: 'Todos' },
		{ value: 'pendiente', label: 'Pendiente' },
		{ value: 'en_proceso', label: 'En Proceso' },
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

	function priorityBadge(priority) {
		const map = { alta: 'badge-danger', media: 'badge-warning', baja: 'badge-info' };
		return map[priority] || 'badge-gray';
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Mis Tareas</h1>
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
										{#if task.estado !== 'completada'}
											<button class="btn btn-success btn-sm" onclick={() => handleComplete(task.id)}>
												Completar
											</button>
										{:else}
											<span class="text-secondary text-sm">Completada</span>
										{/if}
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
