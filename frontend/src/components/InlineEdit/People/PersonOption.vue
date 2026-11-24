<template>
	<div class="flex min-w-0 justify-between gap-2">
		<div class="truncate">{{ label }}</div>
		<div class="truncate text-p-xs text-ink-gray-6">{{ email }}</div>
	</div>
</template>

<script setup lang="ts">
/** A person in a picker list: their name, then their email. */
defineProps<{ label: string; email: string }>()
</script>
