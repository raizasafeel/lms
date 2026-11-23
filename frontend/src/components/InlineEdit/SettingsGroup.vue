<template>
	<section class="space-y-3">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-9">{{ title }}</h2>
			<p v-if="description" class="text-p-sm text-ink-gray-6">
				{{ description }}
			</p>
		</div>
		<div class="divide-y divide-outline-gray-1">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
/** A titled settings section: one sentence, then its rows split by hairlines. */
defineProps<{ title: string; description?: string }>()
</script>
