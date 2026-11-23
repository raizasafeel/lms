<template>
	<div
		class="grid gap-1.5"
		:class="columns === 9 ? 'grid-cols-9' : 'grid-cols-6'"
		role="group"
		:aria-label="__('Thumbnail icon')"
	>
		<button
			v-for="name in COURSE_ICONS"
			:key="name"
			type="button"
			class="flex aspect-square items-center justify-center rounded-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			:class="
				isPicked(name)
					? 'bg-surface-gray-3 text-ink-gray-9'
					: 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8'
			"
			:aria-label="name.replace(/-/g, ' ')"
			:aria-pressed="isPicked(name)"
			@click="icon = name"
		>
			<span :class="[courseIcon(name), 'size-4']" aria-hidden="true" />
		</button>
	</div>
</template>

<script setup lang="ts">
import { COURSE_ICONS, courseIcon } from '@/utils/courseIcons'

/** The course thumbnail icons as a grid; an empty value reads as the open book. */
withDefaults(defineProps<{ columns?: 6 | 9 }>(), { columns: 6 })

const icon = defineModel<string | null | undefined>()

const isPicked = (name: string): boolean =>
	courseIcon(icon.value) === courseIcon(name)
</script>
