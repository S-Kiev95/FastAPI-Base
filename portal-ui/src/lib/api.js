/**
 * API Client — Portal Seguros BK
 * Wrapper centralizado para comunicación con el backend FastAPI.
 */

import { goto } from '$app/navigation';
import { base } from '$app/paths';

/* ── Helpers ── */

function getToken() {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('portal_token');
}

export function getOrgSlug() {
	if (typeof localStorage === 'undefined') return '';
	return localStorage.getItem('portal_org_slug') || '';
}

function orgBase() {
	return `/api/orgs/${getOrgSlug()}/seguros`;
}

/* ── Fetch genérico ── */

export async function apiFetch(path, options = {}) {
	const token = getToken();
	const headers = {
		'Content-Type': 'application/json',
		...(options.headers || {})
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(path, {
		...options,
		headers
	});

	if (res.status === 401 || res.status === 403) {
		localStorage.removeItem('portal_token');
		localStorage.removeItem('portal_org_slug');
		goto(`${base}/login`);
		throw new Error('No autorizado');
	}

	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail || body.message || `Error ${res.status}`);
	}

	if (res.status === 204) return null;
	return res.json();
}

/* ── Auth ── */

export async function login(email, password) {
	const res = await fetch('/auth/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});

	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail || 'Credenciales inválidas');
	}

	const data = await res.json();
	localStorage.setItem('portal_token', data.access_token);
	if (data.org_slug) {
		localStorage.setItem('portal_org_slug', data.org_slug);
	}
	return data;
}

export function logout() {
	localStorage.removeItem('portal_token');
	localStorage.removeItem('portal_org_slug');
	goto(`${base}/login`);
}

/* ── Clientes ── */

export function getClients(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/clientes${qs ? '?' + qs : ''}`);
}

export function getClient(id) {
	return apiFetch(`${orgBase()}/clientes/${id}`);
}

export function createClient(data) {
	return apiFetch(`${orgBase()}/clientes`, { method: 'POST', body: JSON.stringify(data) });
}

export function updateClient(id, data) {
	return apiFetch(`${orgBase()}/clientes/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteClient(id) {
	return apiFetch(`${orgBase()}/clientes/${id}`, { method: 'DELETE' });
}

export function getClientVehicles(id) {
	return apiFetch(`${orgBase()}/clientes/${id}/vehiculos`);
}

export function getClientPolicies(id) {
	return apiFetch(`${orgBase()}/clientes/${id}/polizas`);
}

export function searchClients(q) {
	return apiFetch(`${orgBase()}/clientes?search=${encodeURIComponent(q)}`);
}

/* ── Vehículos ── */

export function getVehicles(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/vehiculos${qs ? '?' + qs : ''}`);
}

export function createVehicle(data) {
	return apiFetch(`${orgBase()}/vehiculos`, { method: 'POST', body: JSON.stringify(data) });
}

/* ── Aseguradoras ── */

export function getInsurers(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/aseguradoras${qs ? '?' + qs : ''}`);
}

export function getInsurer(id) {
	return apiFetch(`${orgBase()}/aseguradoras/${id}`);
}

export function createInsurer(data) {
	return apiFetch(`${orgBase()}/aseguradoras`, { method: 'POST', body: JSON.stringify(data) });
}

/* ── Pólizas ── */

export function getPolicies(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/polizas${qs ? '?' + qs : ''}`);
}

export function getPolicy(id) {
	return apiFetch(`${orgBase()}/polizas/${id}`);
}

export function createPolicy(data) {
	return apiFetch(`${orgBase()}/polizas`, { method: 'POST', body: JSON.stringify(data) });
}

export function getExpiringPolicies(days = 30) {
	return apiFetch(`${orgBase()}/polizas/por-vencer?dias=${days}`);
}

export function renewPolicy(id, data) {
	return apiFetch(`${orgBase()}/polizas/${id}/renovar`, { method: 'POST', body: JSON.stringify(data) });
}

export function getPolicyInstallments(id) {
	return apiFetch(`${orgBase()}/polizas/${id}/cuotas`);
}

export function getPolicyClaims(id) {
	return apiFetch(`${orgBase()}/polizas/${id}/siniestros`);
}

/* ── Cuotas ── */

export function getInstallments(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/cuotas${qs ? '?' + qs : ''}`);
}

export function getOverdueInstallments() {
	return apiFetch(`${orgBase()}/cuotas/vencidas`);
}

export function payInstallment(id, data = {}) {
	return apiFetch(`${orgBase()}/cuotas/${id}/pagar`, { method: 'POST', body: JSON.stringify(data) });
}

/* ── Siniestros ── */

export function getClaims(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/siniestros${qs ? '?' + qs : ''}`);
}

export function getClaim(id) {
	return apiFetch(`${orgBase()}/siniestros/${id}`);
}

export function createClaim(data) {
	return apiFetch(`${orgBase()}/siniestros`, { method: 'POST', body: JSON.stringify(data) });
}

export function getClaimDocuments(id) {
	return apiFetch(`${orgBase()}/siniestros/${id}/documentos`);
}

export function addClaimDocument(id, data) {
	return apiFetch(`${orgBase()}/siniestros/${id}/documentos`, { method: 'POST', body: JSON.stringify(data) });
}

export function markDocumentReceived(claimId, docId) {
	return apiFetch(`${orgBase()}/siniestros/${claimId}/documentos/${docId}/recibido`, { method: 'PUT' });
}

/* ── Talleres ── */

export function getWorkshops(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/talleres${qs ? '?' + qs : ''}`);
}

export function createWorkshop(data) {
	return apiFetch(`${orgBase()}/talleres`, { method: 'POST', body: JSON.stringify(data) });
}

/* ── Tareas ── */

export function getTasks(params = {}) {
	const qs = new URLSearchParams(params).toString();
	return apiFetch(`${orgBase()}/tareas${qs ? '?' + qs : ''}`);
}

export function getMyTasks() {
	return apiFetch(`${orgBase()}/tareas/mis-tareas`);
}

export function createTask(data) {
	return apiFetch(`${orgBase()}/tareas`, { method: 'POST', body: JSON.stringify(data) });
}

export function completeTask(id) {
	return apiFetch(`${orgBase()}/tareas/${id}/completar`, { method: 'PUT' });
}

export function getOverdueTasks() {
	return apiFetch(`${orgBase()}/tareas/vencidas`);
}

/* ── Mensajes ── */

export function getInbox() {
	return apiFetch(`${orgBase()}/mensajes/inbox`);
}

export function getSent() {
	return apiFetch(`${orgBase()}/mensajes/enviados`);
}

export function sendMessage(data) {
	return apiFetch(`${orgBase()}/mensajes`, { method: 'POST', body: JSON.stringify(data) });
}

export function getUnreadCount() {
	return apiFetch(`${orgBase()}/mensajes/no-leidos/count`);
}

export function markRead(id) {
	return apiFetch(`${orgBase()}/mensajes/${id}/leer`, { method: 'PUT' });
}

/* ── Dashboard ── */

export function getDashboard() {
	return apiFetch(`${orgBase()}/dashboard`);
}

export function getUpcomingExpirations(days = 30) {
	return apiFetch(`${orgBase()}/dashboard/proximos-vencimientos?days=${days}`);
}
