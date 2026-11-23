<template>
	<textarea
		ref="field"
		:value="modelValue ?? ''"
		rows="1"
		:placeholder="placeholder"
		:aria-label="placeholder"
		class="-mx-1.5 block w-[calc(100%+0.75rem)] resize-none overflow-hidden rounded-4 border-0 bg-transparent px-1.5 py-0.5 placeholder:text-ink-gray-4 hover:bg-surface-gray-2 focus:bg-transparent focus:ring-2 focus:ring-outline-gray-3"
		:class="missing && 'bg-surface-red-1 ring-2 ring-outline-red-3'"
		@input="onInput"
		@keydown.enter.prevent="emit('enter')"
	/>
</template>

<script setup lang="ts">
import { nextTick, onMounted, useTemplateRef, watch } from 'vue'

/** A single-line field that reads as finished text until hovered. */
const props = defineProps<{
	modelValue?: string | null
	placeholder: string
	missing?: boolean
}>()

const emit = defineEmits<{
	'update:modelValue': [value: string]
	enter: []
}>()

const textarea = useTemplateRef<HTMLTextAreaElement>('field')

function fitHeight(): void {
	const element = textarea.value
	if (!element) return
	element.style.height = 'auto'
	element.style.height = `${element.scrollHeight}px`
}

function onInput(event: Event): void {
	emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
	fitHeight()
}

onMounted(fitHeight)
watch(
	() => props.modelValue,
	() => nextTick(fitHeight)
)

defineExpose({ focus: () => textarea.value?.focus() })
</script>
