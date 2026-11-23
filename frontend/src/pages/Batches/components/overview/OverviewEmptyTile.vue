<template>
	<div
		class="flex flex-col items-center gap-2 rounded-6 border border-dashed border-outline-gray-3 px-6 py-8 text-center"
	>
		<span
			class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2"
		>
			<span class="size-5 text-ink-gray-6" :class="icon" aria-hidden="true" />
		</span>
		<span class="text-base-semibold text-ink-gray-9">{{ title }}</span>
		<span class="text-p-sm text-ink-gray-6">{{ description }}</span>
		<div class="mt-2 flex flex-wrap justify-center gap-2">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
/** Dashed call to action for an empty overview section. */
defineProps<{ icon: string; title: string; description: string }>()
</script>
