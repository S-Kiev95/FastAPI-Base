<script>
	let { label = '', value = 0, format = 'number', accent = 'primary' } = $props();

	function formatValue(val, fmt) {
		if (fmt === 'currency') return `$${val.toLocaleString()}`;
		if (fmt === 'number') return val.toLocaleString();
		return val;
	}

	const accentColors = {
		primary: '#2563EB',
		success: '#16A34A',
		warning: '#D97706',
		info: '#0891B2',
	};
</script>

<div class="kpi card" style="border-left: 4px solid {accentColors[accent] || accentColors.primary}">
	<div class="kpi-value">{formatValue(value, format)}</div>
	<div class="kpi-label text-secondary text-sm">{label}</div>
</div>

<style>
	.kpi {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}
	.kpi-value {
		font-size: 28px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		line-height: 1.2;
	}
	.kpi-label {
		font-weight: 500;
	}
</style>
