<script>
	let { columns = [], data = [], onRowClick = null } = $props();

	let sortKey = $state('');
	let sortAsc = $state(true);

	function handleSort(key) {
		if (sortKey === key) {
			sortAsc = !sortAsc;
		} else {
			sortKey = key;
			sortAsc = true;
		}
	}

	let sortedData = $state([]);

	$effect(() => {
		if (!sortKey || !data) {
			sortedData = data || [];
			return;
		}
		sortedData = [...data].sort((a, b) => {
			const aVal = a[sortKey] ?? '';
			const bVal = b[sortKey] ?? '';
			if (aVal < bVal) return sortAsc ? -1 : 1;
			if (aVal > bVal) return sortAsc ? 1 : -1;
			return 0;
		});
	});
</script>

<div class="table-wrapper card" style="padding: 0; overflow: hidden;">
	{#if data && data.length > 0}
		<table>
			<thead>
				<tr>
					{#each columns as col}
						<th
							style="cursor: pointer; user-select: none;"
							onclick={() => handleSort(col.key)}
						>
							{col.label}
							{#if sortKey === col.key}
								<span>{sortAsc ? ' ↑' : ' ↓'}</span>
							{/if}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each sortedData as row}
					<tr
						style={onRowClick ? 'cursor: pointer;' : ''}
						onclick={() => onRowClick && onRowClick(row)}
					>
						{#each columns as col}
							<td>
								{#if col.render}
									{@html col.render(row[col.key], row)}
								{:else}
									{row[col.key] ?? '—'}
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<div class="empty-state">
			<p>No hay datos para mostrar.</p>
		</div>
	{/if}
</div>
