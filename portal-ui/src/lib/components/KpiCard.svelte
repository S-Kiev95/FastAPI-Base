<script>
	let { label = '', value = 0, color = 'primary' } = $props();

	const accentColors = {
		primary: '#2563EB',
		success: '#16A34A',
		warning: '#D97706',
		danger: '#DC2626',
		info: '#0891B2',
	};

	function formatValue(val) {
		if (typeof val === 'number') return val.toLocaleString();
		return val;
	}
</script>

<div class="kpi card" style="border-left: 4px solid {accentColors[color] || accentColors.primary}">
	<div class="kpi-value">{formatValue(value)}</div>
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
