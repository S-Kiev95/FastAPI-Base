<script>
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getOverdueInstallments, payInstallment } from '$lib/api.js';

	let installments = $state([]);
	let loading = $state(true);
	let error = $state('');
	let payModalOpen = $state(false);
	let selectedInstallment = $state(null);
	let payLoading = $state(false);
	let payError = $state('');

	onMount(async () => {
		await loadInstallments();
	});

	async function loadInstallments() {
		loading = true;
		error = '';
		try {
			installments = await getOverdueInstallments() || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function openPayModal(inst) {
		selectedInstallment = inst;
		payError = '';
		payModalOpen = true;
	}

	async function handlePay() {
		if (!selectedInstallment) return;
		payLoading = true;
		payError = '';
		try {
			await payInstallment(selectedInstallment.id, {
				fecha_pago: new Date().toISOString().split('T')[0]
			});
			payModalOpen = false;
			selectedInstallment = null;
			await loadInstallments();
		} catch (err) {
			payError = err.message;
		} finally {
			payLoading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Cuotas Vencidas</h1>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if installments.length > 0}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>Poliza</th>
								<th>N. Cuota</th>
								<th>Monto</th>
								<th>Vencimiento</th>
								<th>Estado</th>
								<th>Acciones</th>
							</tr>
						</thead>
						<tbody>
							{#each installments as inst}
								<tr>
									<td class="mono">{inst.poliza_numero || inst.poliza_id || '—'}</td>
									<td>{inst.numero_cuota ?? inst.numero ?? '—'}</td>
									<td>{inst.monto?.toLocaleString() ?? '—'}</td>
									<td>{inst.fecha_vencimiento || '—'}</td>
									<td><StatusBadge status={inst.pagada ? 'pagada' : (inst.fecha_vencimiento && new Date(inst.fecha_vencimiento) < new Date() ? 'vencido' : 'pendiente')} /></td>
									<td>
										{#if !inst.pagada}
										<button class="btn btn-success btn-sm" onclick={() => openPayModal(inst)}>
											Registrar Pago
										</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="empty-state"><p>No hay cuotas vencidas.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>

<Modal open={payModalOpen} title="Confirmar Pago" onClose={() => payModalOpen = false}>
	{#if selectedInstallment}
		<p style="margin-bottom: var(--space-4)">
			Confirmar el pago de la cuota #{selectedInstallment.numero_cuota ?? selectedInstallment.numero ?? ''} por
			<strong>{selectedInstallment.monto?.toLocaleString() ?? '—'}</strong>?
		</p>

		{#if payError}
			<div class="alert alert-danger">{payError}</div>
		{/if}

		<div style="display: flex; gap: var(--space-3); justify-content: flex-end;">
			<button class="btn btn-ghost" onclick={() => payModalOpen = false}>Cancelar</button>
			<button class="btn btn-success" onclick={handlePay} disabled={payLoading}>
				{payLoading ? 'Procesando…' : 'Confirmar Pago'}
			</button>
		</div>
	{/if}
</Modal>
