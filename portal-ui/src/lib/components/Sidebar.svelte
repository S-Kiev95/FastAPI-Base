<script>
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { logout } from '$lib/api.js';

	const navItems = [
		{ href: `${base}/dashboard`, label: 'Dashboard', icon: 'chart' },
		{ href: `${base}/clientes`, label: 'Clientes', icon: 'users' },
		{ href: `${base}/polizas`, label: 'Polizas', icon: 'shield' },
		{ href: `${base}/cuotas`, label: 'Cuotas', icon: 'dollar' },
		{ href: `${base}/siniestros`, label: 'Siniestros', icon: 'alert' },
		{ href: `${base}/aseguradoras`, label: 'Aseguradoras', icon: 'building' },
		{ href: `${base}/talleres`, label: 'Talleres', icon: 'wrench' },
		{ href: `${base}/tareas`, label: 'Tareas', icon: 'clipboard' },
		{ href: `${base}/mensajes`, label: 'Mensajes', icon: 'mail' },
		{ href: `${base}/equipo`, label: 'Equipo', icon: 'team' },
	];

	function isActive(href, currentPath) {
		if (href === `${base}/dashboard`) {
			return currentPath === `${base}` || currentPath === `${base}/` || currentPath === `${base}/dashboard`;
		}
		return currentPath.startsWith(href);
	}
</script>

<aside class="sidebar">
	<div class="sidebar-header">
		<span class="logo">Seguros BK</span>
		<span class="badge badge-info">Portal</span>
	</div>

	<nav class="sidebar-nav">
		{#each navItems as item}
			<a
				href={item.href}
				class="nav-item"
				class:active={isActive(item.href, $page.url.pathname)}
			>
				<span class="nav-icon">
					{#if item.icon === 'chart'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="12" width="4" height="9"/><rect x="10" y="8" width="4" height="13"/><rect x="17" y="3" width="4" height="18"/></svg>
					{:else if item.icon === 'users'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					{:else if item.icon === 'shield'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
					{:else if item.icon === 'dollar'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
					{:else if item.icon === 'alert'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
					{:else if item.icon === 'building'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><line x1="8" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="16" y2="14"/></svg>
					{:else if item.icon === 'wrench'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
					{:else if item.icon === 'clipboard'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
					{:else if item.icon === 'mail'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
					{:else if item.icon === 'team'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					{/if}
				</span>
				<span class="nav-label">{item.label}</span>
			</a>
		{/each}
	</nav>

	<div class="sidebar-footer">
		<button class="btn btn-ghost" style="width:100%" onclick={logout}>
			Cerrar sesion
		</button>
	</div>
</aside>

<style>
	.sidebar {
		position: fixed;
		top: 0;
		left: 0;
		width: var(--sidebar-width);
		height: 100vh;
		background: var(--color-surface);
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		z-index: 20;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-4) var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.logo {
		font-size: 16px;
		font-weight: 700;
		color: var(--color-text-primary);
	}

	.sidebar-nav {
		flex: 1;
		padding: var(--space-2) var(--space-2);
		overflow-y: auto;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		text-decoration: none;
		font-size: 14px;
		font-weight: 500;
		transition: all 150ms ease-out;
	}

	.nav-item:hover {
		background: var(--color-surface-muted);
		color: var(--color-text-primary);
		text-decoration: none;
	}

	.nav-item.active {
		background: var(--color-primary-soft);
		color: var(--color-primary);
		font-weight: 600;
	}

	.nav-icon {
		width: 20px;
		height: 18px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.sidebar-footer {
		padding: var(--space-3);
		border-top: 1px solid var(--color-border);
	}

	@media (max-width: 768px) {
		.sidebar {
			transform: translateX(-100%);
		}
	}
</style>
