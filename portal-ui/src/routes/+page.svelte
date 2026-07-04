<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	onMount(() => {
		const token = localStorage.getItem('portal_token');
		goto(token ? `${base}/dashboard` : `${base}/login`);
	});
</script>

<div class="loading">
	<div class="spinner"></div>
</div>
