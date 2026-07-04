<script>
	import { onMount } from 'svelte';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import { getInbox, getSent, sendMessage, getUnreadCount, markRead, getOrgUsers } from '$lib/api.js';

	let activeTab = $state('inbox');
	let inbox = $state([]);
	let sent = $state([]);
	let unreadCount = $state(0);
	let loading = $state(true);
	let error = $state('');

	// Compose modal
	let composeOpen = $state(false);
	let usuarios = $state([]);
	let composeForm = $state({ destinatario_id: '', asunto: '', contenido: '' });
	let sendLoading = $state(false);
	let sendError = $state('');

	onMount(async () => {
		await loadMessages();
		usuarios = (await getOrgUsers().catch(() => [])) || [];
	});

	async function loadMessages() {
		loading = true;
		error = '';
		try {
			const [inb, snt, count] = await Promise.all([
				getInbox(),
				getSent().catch(() => []),
				getUnreadCount().catch(() => ({ count: 0 }))
			]);
			inbox = inb || [];
			sent = snt || [];
			unreadCount = count?.count ?? count ?? 0;
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	async function handleMarkRead(msg) {
		if (msg.leido) return;
		try {
			await markRead(msg.id);
			inbox = inbox.map(m =>
				m.id === msg.id ? { ...m, leido: true } : m
			);
			unreadCount = Math.max(0, unreadCount - 1);
		} catch (err) {
			// silently fail
		}
	}

	function openCompose() {
		composeForm = { destinatario_id: '', asunto: '', contenido: '' };
		sendError = '';
		composeOpen = true;
	}

	async function handleSend(e) {
		e.preventDefault();
		sendLoading = true;
		sendError = '';
		try {
			const data = {
				...composeForm,
				destinatario_id: parseInt(composeForm.destinatario_id)
			};
			await sendMessage(data);
			composeOpen = false;
			await loadMessages();
		} catch (err) {
			sendError = err.message;
		} finally {
			sendLoading = false;
		}
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>
			Mensajes
			{#if unreadCount > 0}
				<span class="badge badge-danger" style="font-size: 14px; vertical-align: middle; margin-left: var(--space-2);">{unreadCount}</span>
			{/if}
		</h1>
		<button class="btn btn-primary" onclick={openCompose}>+ Nuevo Mensaje</button>
	</div>

	<div class="tabs">
		<button class="tab" class:active={activeTab === 'inbox'} onclick={() => activeTab = 'inbox'}>
			Bandeja de entrada ({inbox.length})
		</button>
		<button class="tab" class:active={activeTab === 'sent'} onclick={() => activeTab = 'sent'}>
			Enviados ({sent.length})
		</button>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if activeTab === 'inbox'}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if inbox.length > 0}
				<table>
					<thead>
						<tr>
							<th></th>
							<th>De</th>
							<th>Asunto</th>
							<th>Fecha</th>
						</tr>
					</thead>
					<tbody>
						{#each inbox as msg}
							<tr
								style="cursor:pointer"
								class:unread={!msg.leido}
								onclick={() => handleMarkRead(msg)}
							>
								<td style="width:10px">
									{#if !msg.leido}
										<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--color-primary);"></span>
									{/if}
								</td>
								<td style={!msg.leido ? 'font-weight:600' : ''}>{msg.remitente_nombre || msg.remitente_id || '—'}</td>
								<td style={!msg.leido ? 'font-weight:600' : ''}>{msg.asunto || '(sin asunto)'}</td>
								<td class="text-sm text-secondary">{msg.fecha_envio || msg.created_at || '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<div class="empty-state"><p>No hay mensajes en la bandeja de entrada.</p></div>
			{/if}
		</div>
	{:else}
		<div class="card" style="padding:0; overflow:hidden;">
			{#if sent.length > 0}
				<table>
					<thead>
						<tr>
							<th>Para</th>
							<th>Asunto</th>
							<th>Fecha</th>
						</tr>
					</thead>
					<tbody>
						{#each sent as msg}
							<tr>
								<td>{msg.destinatario_nombre || msg.destinatario_id || '—'}</td>
								<td>{msg.asunto || '(sin asunto)'}</td>
								<td class="text-sm text-secondary">{msg.fecha_envio || msg.created_at || '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<div class="empty-state"><p>No hay mensajes enviados.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>

<Modal open={composeOpen} title="Nuevo Mensaje" onClose={() => composeOpen = false}>
	<form onsubmit={handleSend}>
		<div class="form-group">
			<label for="destinatario">Destinatario</label>
			<select id="destinatario" bind:value={composeForm.destinatario_id} required>
					<option value="">Seleccionar destinatario…</option>
					{#each usuarios as u}
						<option value={u.id}>{u.nombre}</option>
					{/each}
				</select>
		</div>
		<div class="form-group">
			<label for="asunto">Asunto</label>
			<input id="asunto" type="text" bind:value={composeForm.asunto} required />
		</div>
		<div class="form-group">
			<label for="cuerpo">Mensaje</label>
			<textarea id="cuerpo" bind:value={composeForm.contenido} required rows="5"></textarea>
		</div>

		{#if sendError}
			<div class="alert alert-danger">{sendError}</div>
		{/if}

		<div style="display: flex; gap: var(--space-3); justify-content: flex-end; margin-top: var(--space-4)">
			<button type="button" class="btn btn-ghost" onclick={() => composeOpen = false}>Cancelar</button>
			<button type="submit" class="btn btn-primary" disabled={sendLoading}>
				{sendLoading ? 'Enviando…' : 'Enviar'}
			</button>
		</div>
	</form>
</Modal>

<style>
	tr.unread td {
		background: var(--color-primary-soft);
	}
</style>
