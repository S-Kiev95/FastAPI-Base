/**
 * Cliente API para el admin panel.
 * En dev usa proxy de Vite, en producción usa la misma origin.
 */
const BASE = '';

/**
 * Fetch wrapper con auth token y manejo de errores.
 */
export async function apiFetch(path, options = {}) {
	const token = typeof localStorage !== 'undefined' ? localStorage.getItem('admin_token') : null;

	const headers = {
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {}),
		...options.headers
	};

	const res = await fetch(`${BASE}${path}`, { ...options, headers });

	if (res.status === 401 || res.status === 403) {
		if (typeof localStorage !== 'undefined') {
			localStorage.removeItem('admin_token');
		}
		if (typeof window !== 'undefined') {
			window.location.href = '/admin/login';
		}
		throw new Error('No autorizado');
	}

	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail || `Error ${res.status}`);
	}

	return res.json();
}

// ---- Dashboard ----
export const getDashboard = () => apiFetch('/api/admin/dashboard');

// ---- Organizations ----
export const getOrganizations = (params = '') => apiFetch(`/api/admin/organizations?${params}`);
export const getOrganization = (id) => apiFetch(`/api/admin/organizations/${id}`);
export const toggleOrgActive = (id, active) =>
	apiFetch(`/api/admin/organizations/${id}/toggle-active?is_active=${active}`, { method: 'PATCH' });

// ---- Users ----
export const getUsers = (params = '') => apiFetch(`/api/admin/users?${params}`);
export const toggleUserActive = (id, active) =>
	apiFetch(`/api/admin/users/${id}/toggle-active?is_active=${active}`, { method: 'PATCH' });

// ---- Subscriptions ----
export const getSubscriptions = (params = '') => apiFetch(`/api/admin/subscriptions?${params}`);
export const getSubscriptionStats = () => apiFetch('/api/admin/subscriptions/stats');

// ---- Payments ----
export const getPayments = (params = '') => apiFetch(`/api/admin/payments?${params}`);

// ---- Metrics ----
export const getMetrics = () => apiFetch('/api/admin/metrics');

// ---- Impersonate ----
export const impersonateUser = (userId) =>
	apiFetch(`/api/admin/impersonate/${userId}`, { method: 'POST' });

// ---- Auth ----
export async function login(email, password) {
	const res = await fetch(`${BASE}/auth/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	if (!res.ok) throw new Error('Credenciales inválidas');
	const data = await res.json();
	localStorage.setItem('admin_token', data.access_token);
	return data;
}

export function logout() {
	localStorage.removeItem('admin_token');
	window.location.href = '/admin/login';
}

export function isAuthenticated() {
	return typeof localStorage !== 'undefined' && !!localStorage.getItem('admin_token');
}

// ---- Setup Wizard ----
/**
 * Check system setup status (no auth required).
 * Returns { configured, env_file_exists, required_vars_set, missing_vars, ... }
 */
export async function getSetupStatus() {
	const res = await fetch(`${BASE}/setup/status`);
	if (!res.ok) throw new Error(`Setup status error ${res.status}`);
	return res.json();
}
