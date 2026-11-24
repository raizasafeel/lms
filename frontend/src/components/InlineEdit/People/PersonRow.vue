<template>
	<li class="flex items-center gap-3 py-2.5">
		<Avatar :image="image" :label="name" size="lg" />
		<div class="min-w-0 flex-1">
			<div class="truncate text-base-medium text-ink-gray-9">{{ name }}</div>
			<div class="truncate text-p-sm text-ink-gray-6">{{ description }}</div>
		</div>
		<slot name="actions" />
	</li>
</template>

<script setup lang="ts">
import { Avatar } from 'frappe-ui'

/** One person in a People list: who they are, what they do, then their controls. */
defineProps<{ name: string; image?: string; description: string }>()
</script>
