<template>
	<div data-testid="search-preview">
		<p class="truncate text-p-sm text-ink-green-6" dir="ltr">{{ url }}</p>
		<p class="truncate text-lg text-ink-blue-5">
			{{ title || __('Untitled') }}
		</p>
		<p
			class="mt-0.5 line-clamp-2 text-p-sm"
			:class="description ? 'text-ink-gray-7' : 'text-ink-gray-6'"
		>
			{{ description || __('Add a description to show here.') }}
		</p>
	</div>
</template>

<script setup lang="ts">
/** A search result as engines show it: address, title, then the description. */
defineProps<{
	url: string
	title?: string | null
	description?: string | null
}>()
</script>
