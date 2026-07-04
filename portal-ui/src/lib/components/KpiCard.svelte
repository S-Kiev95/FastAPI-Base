<script>
	let { label = '', value = 0, color = 'primary' } = $props();

	const accentVar = {
		primary: 'var(--color-primary)',
		success: 'var(--color-success)',
		warning: 'var(--color-warning)',
		danger: 'var(--color-danger)',
		info: 'var(--color-info)',
		accent: 'var(--color-accent)',
	};

	function formatValue(val) {
		if (typeof val === 'number') return val.toLocaleString();
		return val;
	}
</script>

<div class="kpi card" style="--accent: {accentVar[color] || accentVar.primary}">
	<div class="kpi-label">{label}</div>
	<div class="kpi-value">{formatValue(value)}</div>
</div>

<style>
	.kpi {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		border-left: 3px solid var(--accent);
	}
	.kpi-label {
		font-size: 13px;
		font-weight: 500;
		color: var(--color-text-secondary);
	}
	.kpi-value {
		font-size: 30px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		line-height: 1.1;
		letter-spacing: -0.02em;
		color: var(--color-text-primary);
	}
</style>
