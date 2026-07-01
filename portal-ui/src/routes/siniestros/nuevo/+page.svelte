<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import { createClaim, getPolicies } from '$lib/api.js';

	let form = $state({
		poliza_id: '',
		fecha_ocurrencia: '',
		descripcion: '',
		monto_reclamado: '',
		tipo_dano: ''
	});
	let polizas = $state([]);
	let loading = $state(false);
	let error = $state('');

	onMount(async () => {
		polizas = (await getPolicies().catch(() => [])) || [];
	});

	async function handleSubmit(e) {
		e.preventDefault();
		loading = true;
		error = '';
		try {
			const data = {
				...form,
				poliza_id: parseInt(form.poliza_id),
				monto_reclamado: form.monto_reclamado ? parseFloat(form.monto_reclamado) : null,
			};
			if (!data.tipo_dano) delete data.tipo_dano;
			await createClaim(data);
			goto(`${base}/siniestros`);
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Nuevo Siniestro</h1>
		<a href="{base}/siniestros" class="btn btn-secondary">Cancelar</a>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	<div class="card">
		<form onsubmit={handleSubmit}>
			<div class="form-row">
				<div class="form-group">
					<label for="poliza_id">Poliza</label>
					<select id="poliza_id" bind:value={form.poliza_id} required>
						<option value="">Seleccionar poliza...</option>
						{#each polizas as p}
							<option value={p.id}>{p.numero_poliza} — {p.cliente_nombre || ('Cliente ' + p.cliente_id)}</option>
						{/each}
					</select>
				</div>
				<div class="form-group">
					<label for="fecha_siniestro">Fecha del Siniestro</label>
					<input id="fecha_siniestro" type="date" bind:value={form.fecha_ocurrencia} required />
				</div>
			</div>

			<div class="form-row">
				<div class="form-group">
					<label for="tipo_siniestro">Tipo de Daño</label>
					<select id="tipo_siniestro" bind:value={form.tipo_dano}>
						<option value="">Seleccionar...</option>
						<option value="dano_propio">Daño propio</option>
						<option value="dano_tercero">Daño a tercero</option>
						<option value="robo_total">Robo total</option>
						<option value="robo_parcial">Robo parcial</option>
						<option value="incendio">Incendio</option>
						<option value="otro">Otro</option>
					</select>
				</div>
				<div class="form-group">
					<label for="monto_reclamado">Monto Reclamado</label>
					<input id="monto_reclamado" type="number" step="0.01" bind:value={form.monto_reclamado} />
				</div>
			</div>

			<div class="form-group">
				<label for="descripcion">Descripcion</label>
				<textarea id="descripcion" bind:value={form.descripcion} required rows="4"></textarea>
			</div>

			<div style="display: flex; gap: var(--space-3); margin-top: var(--space-4)">
				<button class="btn btn-primary" type="submit" disabled={loading}>
					{loading ? 'Guardando...' : 'Crear Siniestro'}
				</button>
			</div>
		</form>
	</div>
</PortalLayout>
