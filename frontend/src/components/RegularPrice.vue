<template>
	<s
		v-if="price"
		class="font-normal text-ink-gray-6"
		data-testid="regular-price"
	>
		<span class="sr-only">{{ __('Regular price') }}</span>
		{{ price }}
	</s>
</template>

<script setup lang="ts">
/** The regular price a learner's regional price replaces, struck through. */
defineProps<{ price?: string | null }>()
</script>
