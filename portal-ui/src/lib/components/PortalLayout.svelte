<script>
	import Sidebar from './Sidebar.svelte';
	let { children } = $props();
</script>

<div class="portal-layout">
	<Sidebar />
	<main class="portal-main">
		{@render children()}
	</main>
</div>

<style>
	.portal-layout {
		display: flex;
		min-height: 100vh;
	}

	.portal-main {
		flex: 1;
		margin-left: var(--sidebar-width);
		padding: var(--space-6);
		max-width: 1280px;
	}

	@media (max-width: 768px) {
		.portal-main {
			margin-left: 0;
			padding: var(--space-4);
		}
	}
</style>
