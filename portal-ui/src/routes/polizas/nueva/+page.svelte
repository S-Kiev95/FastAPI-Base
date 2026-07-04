<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createPolicy, getClients, getInsurers, getClientVehicles } from '$lib/api.js';

	let form = $state({
		cliente_id: '',
		vehiculo_id: '',
		aseguradora_id: '',
		numero_poliza: '',
		tipo_seguro: '',
		vigente_desde: '',
		vigente_hasta: '',
		prima_total: '',
		moneda: 'UYU',
		total_cuotas: ''
	});
	let clientes = $state([]);
	let aseguradoras = $state([]);
	let vehiculos = $state([]);
	let loading = $state(false);
	let error = $state('');

	onMount(async () => {
		const [cl, as] = await Promise.all([
			getClients().catch(() => []),
			getInsurers().catch(() => [])
		]);
		clientes = cl || [];
		aseguradoras = as || [];
	});

	async function onClienteChange() {
		form.vehiculo_id = '';
		vehiculos = form.cliente_id ? (await getClientVehicles(form.cliente_id).catch(() => [])) : [];
	}

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			const data = {
				...form,
				cliente_id: parseInt(form.cliente_id),
				vehiculo_id: form.vehiculo_id ? parseInt(form.vehiculo_id) : null,
				aseguradora_id: parseInt(form.aseguradora_id),
				prima_total: parseFloat(form.prima_total) || 0,
				total_cuotas: parseInt(form.total_cuotas) || 1
			};
			await createPolicy(data);
			goto(`${base}/polizas`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nueva Poliza</h1>
		<a href="{base}/polizas" class="btn btn-secondary">Cancelar</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	<div class="card">
		<form onsubmit={handleSubmit}>
			<div class="form-row">
				<div class="form-group">
					<label for="cliente_id">Cliente</label>
					<select id="cliente_id" bind:value={form.cliente_id} onchange={onClienteChange} required>
						<option value="">Seleccionar cliente…</option>
						{#each clientes as c}
							<option value={c.id}>{c.nombre} {c.apellido}</option>
						{/each}
					</select>
				</div>
				<div class="form-group">
					<label for="vehiculo_id">Vehiculo</label>
					<select id="vehiculo_id" bind:value={form.vehiculo_id} disabled={!form.cliente_id}>
						<option value="">{form.cliente_id ? 'Sin vehiculo' : 'Elegi un cliente primero'}</option>
						{#each vehiculos as v}
							<option value={v.id}>{v.marca} {v.modelo || ''} — {v.matricula}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="aseguradora_id">Aseguradora</label>
					<select id="aseguradora_id" bind:value={form.aseguradora_id} required>
						<option value="">Seleccionar aseguradora…</option>
						{#each aseguradoras as a}
							<option value={a.id}>{a.nombre}</option>
						{/each}
					</select>
				</div>
				<div class="form-group">
					<label for="numero_poliza">Numero de Poliza</label>
					<input id="numero_poliza" type="text" bind:value={form.numero_poliza} required />
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="tipo_seguro">Tipo de Seguro</label>
					<select id="tipo_seguro" bind:value={form.tipo_seguro} required>
						<option value="">Seleccionar…</option>
						<option value="auto">Auto</option>
						<option value="moto">Moto</option>
						<option value="hogar">Hogar</option>
						<option value="vida">Vida</option>
						<option value="comercio">Comercio</option>
						<option value="responsabilidad_civil">Responsabilidad Civil</option>
						<option value="otro">Otro</option>
					</select>
				</div>
				<div class="form-group">
					<label for="moneda">Moneda</label>
					<select id="moneda" bind:value={form.moneda}>
						<option value="UYU">UYU</option>
						<option value="USD">USD</option>
					</select>
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="vigente_desde">Vigente Desde</label>
					<input id="vigente_desde" type="date" bind:value={form.vigente_desde} required />
				</div>
				<div class="form-group">
					<label for="vigente_hasta">Vigente Hasta</label>
					<input id="vigente_hasta" type="date" bind:value={form.vigente_hasta} required />
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="prima_total">Prima Total</label>
					<input id="prima_total" type="number" step="0.01" bind:value={form.prima_total} required />
				</div>
				<div class="form-group">
					<label for="total_cuotas">Total de Cuotas</label>
					<input id="total_cuotas" type="number" min="1" bind:value={form.total_cuotas} required />
				</div>
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando…' : 'Crear Poliza'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
