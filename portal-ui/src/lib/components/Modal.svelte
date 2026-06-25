<script>
	let { open = false, title = '', onClose = () => {}, children } = $props();

	function handleBackdrop(e) {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<div class="modal-backdrop" onclick={handleBackdrop} role="dialog" aria-modal="true">
		<div class="modal-content card">
			<div class="modal-header">
				<h2>{title}</h2>
				<button class="btn btn-ghost btn-sm" onclick={onClose}>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				</button>
			</div>
			<div class="modal-body">
				{@render children()}
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 50;
		padding: var(--space-4);
	}

	.modal-content {
		width: 100%;
		max-width: 560px;
		max-height: 90vh;
		overflow-y: auto;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-4);
	}

	.modal-header h2 {
		font-size: 18px;
		font-weight: 600;
	}

	.modal-body {
		/* children go here */
	}
</style>
