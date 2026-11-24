<template>
	<div class="flex items-center gap-2 ps-2">
		<span
			class="size-4 shrink-0"
			:class="[icon, enabled ? 'text-ink-gray-5' : 'text-ink-gray-4']"
		/>
		<span class="flex-1" :class="!enabled && 'text-ink-gray-6'">
			{{ enabled ? on : off }}
		</span>
		<Switch v-model="enabled" size="sm" :aria-label="on" />
	</div>
</template>

<script setup lang="ts">
import { Switch } from 'frappe-ui'

/** A card fact that reads as text and toggles in place. */
defineProps<{ icon: string; on: string; off: string }>()
const enabled = defineModel<boolean | 0 | 1 | undefined>({ required: true })
</script>
