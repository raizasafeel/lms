<template>
	<div
		ref="frame"
		class="relative w-full overflow-hidden"
		:style="{ height: `${height}px` }"
	>
		<iframe
			v-if="html"
			:srcdoc="html"
			:title="title"
			sandbox=""
			loading="lazy"
			referrerpolicy="no-referrer"
			class="absolute top-0 border-0"
			:style="paperStyle"
		/>
		<div
			v-else-if="loading"
			class="size-full animate-pulse bg-surface-gray-2"
			role="status"
			:aria-label="__('Loading certificate preview')"
		/>
		<div
			v-else
			class="flex size-full items-center justify-center bg-surface-gray-2 px-4 text-center text-p-sm text-ink-gray-6"
		>
			{{ __('Preview unavailable for this design.') }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useElementSize } from '@vueuse/core'

const PAPER_WIDTH = 1122
const PAPER_HEIGHT = 793

withDefaults(
	defineProps<{
		html: string | null
		title: string
		loading?: boolean
	}>(),
	{ loading: false }
)

const frame = ref<HTMLElement | null>(null)
const { width } = useElementSize(frame)

const scale = computed<number>(() => width.value / PAPER_WIDTH)
const height = computed<number>(() => Math.round(PAPER_HEIGHT * scale.value))
const paperStyle = computed<Record<string, string>>(() => ({
	left: '0',
	width: `${PAPER_WIDTH}px`,
	height: `${PAPER_HEIGHT}px`,
	transform: `scale(${scale.value})`,
	transformOrigin: 'top left',
}))
</script>
