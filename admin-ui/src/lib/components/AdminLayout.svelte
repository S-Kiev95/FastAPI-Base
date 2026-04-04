<script>
	import Sidebar from './Sidebar.svelte';
	let { children } = $props();
</script>

<div class="admin-layout">
	<Sidebar />
	<main class="admin-main">
		{@render children()}
	</main>
</div>

<style>
	.admin-layout {
		display: flex;
		min-height: 100vh;
	}

	.admin-main {
		flex: 1;
		margin-left: var(--sidebar-width);
		padding: var(--space-6);
		max-width: 1280px;
	}

	@media (max-width: 768px) {
		.admin-main {
			margin-left: 0;
			padding: var(--space-4);
		}
	}
</style>
