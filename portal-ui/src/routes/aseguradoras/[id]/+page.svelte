<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { getInsurer } from '$lib/api.js';

	let insurer = $state(null);
	let loading = $state(true);
	let error = $state('');

	let insurerId = $page.params.id;

	onMount(async () => {
		try {
			insurer = await getInsurer(insurerId);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});
</script>

<PortalLayout>
	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="alert alert-danger">{error}</div>
	{:else if insurer}
		<div class="page-header">
			<h1>{insurer.nombre}</h1>
			<a href="{base}/aseguradoras" class="btn btn-secondary">Volver</a>
		</div>

		<div class="card" style="margin-bottom: var(--space-6)">
			<div class="detail-grid">
				<div class="detail-item">
					<span class="detail-label">Nombre</span>
					<span>{insurer.nombre}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">RUT</span>
					<span class="mono">{insurer.rut || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Telefono</span>
					<span>{insurer.telefono || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Email</span>
					<span>{insurer.email || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Direccion</span>
					<span>{insurer.direccion || '—'}</span>
				</div>
				<div class="detail-item">
					<span class="detail-label">Sitio Web</span>
					<span>{insurer.sitio_web || '—'}</span>
				</div>
			</div>
		</div>

		{#if insurer.contactos}
			<h2 style="margin-bottom: var(--space-4)">Contactos</h2>
			<div class="card" style="margin-bottom: var(--space-6)">
				{#if Array.isArray(insurer.contactos) && insurer.contactos.length > 0}
					<div class="table-wrapper">
						<table>
							<thead>
								<tr>
									<th>Nombre</th>
									<th>Cargo</th>
									<th>Telefono</th>
									<th>Email</th>
								</tr>
							</thead>
							<tbody>
								{#each insurer.contactos as c}
									<tr>
										<td>{c.nombre || '—'}</td>
										<td>{c.cargo || '—'}</td>
										<td>{c.telefono || '—'}</td>
										<td>{c.email || '—'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else if typeof insurer.contactos === 'object'}
					<pre class="mono" style="white-space: pre-wrap; font-size: 13px;">{JSON.stringify(insurer.contactos, null, 2)}</pre>
				{/if}
			</div>
		{/if}

		{#if insurer.talleres && insurer.talleres.length > 0}
			<h2 style="margin-bottom: var(--space-4)">Talleres Asociados</h2>
			<div class="card" style="padding:0; overflow:hidden;">
				<table>
					<thead>
						<tr>
							<th>Nombre</th>
							<th>Direccion</th>
							<th>Telefono</th>
						</tr>
					</thead>
					<tbody>
						{#each insurer.talleres as t}
							<tr>
								<td>{t.nombre || '—'}</td>
								<td>{t.direccion || '—'}</td>
								<td>{t.telefono || '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</PortalLayout>

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
