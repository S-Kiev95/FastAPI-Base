<script>
	let { status = '', type = 'policy' } = $props();

	const statusMap = {
		// Polizas
		activa: 'badge-success',
		vigente: 'badge-success',
		vencida: 'badge-danger',
		cancelada: 'badge-gray',
		suspendida: 'badge-warning',
		renovada: 'badge-info',
		// Siniestros
		abierto: 'badge-warning',
		en_tramite: 'badge-info',
		en_proceso: 'badge-info',
		liquidado: 'badge-success',
		cerrado: 'badge-success',
		rechazado: 'badge-danger',
		// Cuotas / Tareas
		pendiente: 'badge-warning',
		pagada: 'badge-success',
		vencido: 'badge-danger',
		completada: 'badge-success',
		// Genérico
		activo: 'badge-success',
		inactivo: 'badge-gray',
	};

	function getBadgeClass(s) {
		const key = (s || '').toLowerCase().replace(/\s+/g, '_');
		return statusMap[key] || 'badge-gray';
	}

	function formatLabel(s) {
		if (!s) return '—';
		return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
	}
</script>

<span class="badge {getBadgeClass(status)}">
	{formatLabel(status)}
</span>
