<script>
	// Paginación simple prev/next. hasNext se infiere de si la página vino llena
	// (count === pageSize), sin depender de un total del backend.
	let { page = 0, pageSize = 20, count = 0, onChange = () => {} } = $props();

	let hasPrev = $derived(page > 0);
	let hasNext = $derived(count >= pageSize);
</script>

{#if hasPrev || hasNext}
	<div class="pagination">
		<button class="btn btn-secondary btn-sm" disabled={!hasPrev} onclick={() => onChange(page - 1)}>
			← Anterior
		</button>
		<span class="text-sm text-secondary">Pagina {page + 1}</span>
		<button class="btn btn-secondary btn-sm" disabled={!hasNext} onclick={() => onChange(page + 1)}>
			Siguiente →
		</button>
	</div>
{/if}

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-4);
		margin-top: var(--space-4);
	}
</style>
