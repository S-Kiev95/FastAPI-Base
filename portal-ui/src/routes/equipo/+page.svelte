<script>
	import { onMount } from 'svelte';
	import PortalLayout from '$lib/components/PortalLayout.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { getMembers, getInvitations, createInvitation, revokeInvitation, updateMemberRole, removeMember } from '$lib/api.js';

	let members = $state([]);
	let invitations = $state([]);
	let loading = $state(true);
	let error = $state('');

	// Formulario de invitación
	let inviteEmail = $state('');
	let inviteRole = $state('member');
	let inviteLoading = $state(false);
	let inviteError = $state('');
	let lastLink = $state('');
	let copied = $state(false);

	onMount(load);

	async function load() {
		loading = true;
		error = '';
		try {
			const [m, inv] = await Promise.all([
				getMembers(),
				getInvitations().catch(() => [])
			]);
			members = m || [];
			invitations = inv || [];
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	async function handleInvite(e) {
		e.preventDefault();
		inviteLoading = true;
		inviteError = '';
		copied = false;
		try {
			const res = await createInvitation({ email: inviteEmail, role: inviteRole });
			lastLink = `${location.origin}${res.accept_path}`;
			inviteEmail = '';
			invitations = await getInvitations().catch(() => invitations);
		} catch (err) {
			inviteError = err.message;
		} finally {
			inviteLoading = false;
		}
	}

	async function handleRoleChange(userId, role) {
		try {
			await updateMemberRole(userId, role);
			members = members.map(m => (m.user_id === userId ? { ...m, role } : m));
		} catch (err) {
			error = err.message;
		}
	}

	async function handleRemoveMember(userId) {
		if (!confirm('¿Quitar a este miembro de la organización?')) return;
		try {
			await removeMember(userId);
			members = members.filter(m => m.user_id !== userId);
		} catch (err) {
			error = err.message;
		}
	}

	async function handleRevoke(id) {
		if (!confirm('¿Revocar esta invitación?')) return;
		try {
			await revokeInvitation(id);
			invitations = invitations.filter(i => i.id !== id);
		} catch (err) {
			error = err.message;
		}
	}

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(lastLink);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch { /* ignore */ }
	}

	function fmtDate(d) {
		return d ? String(d).split('T')[0] : '—';
	}
</script>

<PortalLayout>
	<div class="page-header">
		<h1>Equipo</h1>
	</div>

	{#if error}
		<div class="alert alert-danger">{error}</div>
	{/if}

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else}
		<!-- Invitar -->
		<div class="card" style="margin-bottom: var(--space-6)">
			<h2 style="margin-bottom: var(--space-4)">Invitar miembro</h2>
			<form onsubmit={handleInvite}>
				<div class="form-row">
					<div class="form-group">
						<label for="inv-email">Email</label>
						<input id="inv-email" type="email" bind:value={inviteEmail} required placeholder="persona@ejemplo.com" />
					</div>
					<div class="form-group">
						<label for="inv-role">Rol</label>
						<select id="inv-role" bind:value={inviteRole}>
							<option value="viewer">Viewer</option>
							<option value="member">Member</option>
							<option value="admin">Admin</option>
						</select>
					</div>
				</div>
				{#if inviteError}<div class="alert alert-danger">{inviteError}</div>{/if}
				<button class="btn btn-primary" type="submit" disabled={inviteLoading}>
					{inviteLoading ? 'Enviando…' : 'Enviar invitación'}
				</button>
			</form>

			{#if lastLink}
				<div class="alert alert-success" style="margin-top: var(--space-4)">
					<div style="margin-bottom: var(--space-2)">Invitación creada. Compartí este link para que la persona se una:</div>
					<div style="display:flex; gap: var(--space-2); align-items:center;">
						<input type="text" readonly value={lastLink} onclick={(e) => e.target.select()} style="flex:1; font-size:13px;" />
						<button type="button" class="btn btn-secondary btn-sm" onclick={copyLink}>{copied ? '¡Copiado!' : 'Copiar'}</button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Miembros -->
		<h2 style="margin-bottom: var(--space-4)">Miembros ({members.length})</h2>
		<div class="card" style="padding:0; overflow:hidden; margin-bottom: var(--space-6)">
			<table>
				<thead>
					<tr><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th></th></tr>
				</thead>
				<tbody>
					{#each members as m}
						<tr>
							<td>{m.nombre || '—'}</td>
							<td>{m.email || '—'}</td>
							<td>
								{#if m.role === 'owner'}
									<span class="badge badge-info">owner</span>
								{:else}
									<select value={m.role} onchange={(e) => handleRoleChange(m.user_id, e.target.value)} style="height:30px; padding:0 8px; font-size:13px; width:auto;">
										<option value="viewer">viewer</option>
										<option value="member">member</option>
										<option value="admin">admin</option>
									</select>
								{/if}
							</td>
							<td><StatusBadge status={m.is_active ? 'activo' : 'inactivo'} /></td>
							<td style="text-align:right">
								{#if m.role !== 'owner'}
									<button class="btn btn-danger btn-sm" onclick={() => handleRemoveMember(m.user_id)}>Quitar</button>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Invitaciones pendientes -->
		<h2 style="margin-bottom: var(--space-4)">Invitaciones pendientes ({invitations.length})</h2>
		<div class="card" style="padding:0; overflow:hidden;">
			{#if invitations.length > 0}
				<table>
					<thead>
						<tr><th>Email</th><th>Rol</th><th>Expira</th><th></th></tr>
					</thead>
					<tbody>
						{#each invitations as inv}
							<tr>
								<td>{inv.email}</td>
								<td><span class="badge badge-gray">{inv.role}</span></td>
								<td>{fmtDate(inv.expires_at)}</td>
								<td style="text-align:right"><button class="btn btn-danger btn-sm" onclick={() => handleRevoke(inv.id)}>Revocar</button></td>
							</tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<div class="empty-state"><p>No hay invitaciones pendientes.</p></div>
			{/if}
		</div>
	{/if}
</PortalLayout>
