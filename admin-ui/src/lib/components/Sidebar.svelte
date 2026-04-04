<script>
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { logout } from '$lib/api.js';

	const navItems = [
		{ href: `${base}/`, label: 'Dashboard', icon: '⊞' },
		{ href: `${base}/organizations`, label: 'Organizaciones', icon: '⊟' },
		{ href: `${base}/users`, label: 'Usuarios', icon: '⊡' },
		{ href: `${base}/subscriptions`, label: 'Suscripciones', icon: '⊠' },
		{ href: `${base}/payments`, label: 'Pagos', icon: '⊞' },
		{ href: `${base}/metrics`, label: 'Métricas', icon: '⊙' },
	];

	function isActive(href, currentPath) {
		if (href === `${base}/`) return currentPath === `${base}` || currentPath === `${base}/`;
		return currentPath.startsWith(href);
	}
</script>

<aside class="sidebar">
	<div class="sidebar-header">
		<span class="logo">Seguros BK</span>
		<span class="badge badge-info">Admin</span>
	</div>

	<nav class="sidebar-nav">
		{#each navItems as item}
			<a
				href={item.href}
				class="nav-item"
				class:active={isActive(item.href, $page.url.pathname)}
			>
				<span class="nav-icon">{item.icon}</span>
				<span class="nav-label">{item.label}</span>
			</a>
		{/each}
	</nav>

	<div class="sidebar-footer">
		<button class="btn btn-ghost" style="width:100%" onclick={logout}>
			Cerrar sesión
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
		background: var(--color-surface-alt);
		color: var(--color-text-primary);
	}

	.nav-item.active {
		background: rgba(37, 99, 235, 0.1);
		color: var(--color-primary);
	}

	.nav-icon { font-size: 16px; width: 20px; text-align: center; }

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
