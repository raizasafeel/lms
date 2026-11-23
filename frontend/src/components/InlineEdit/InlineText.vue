<template>
	<textarea
		ref="field"
		:value="modelValue ?? ''"
		rows="1"
		:placeholder="placeholder"
		:aria-label="label || placeholder"
		class="block w-full resize-none overflow-hidden px-2.5 py-1.5"
		:class="[OUTLINE_FIELD, missingRing(missing)]"
		@input="onInput"
		@keydown.enter.prevent="emit('enter')"
	/>
</template>

<script setup lang="ts">
import { nextTick, onMounted, useTemplateRef, watch } from 'vue'
import {
	OUTLINE_FIELD,
	missingRing,
} from '@/components/InlineEdit/fieldClasses'

/**
 * A one-paragraph outline field that grows with its text. frappe-ui inputs
 * have a fixed type scale, so a title or intro set at page size needs this.
 */
const props = defineProps<{
	modelValue?: string | null
	placeholder: string
	label?: string
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
	element.style.height = `${element.scrollHeight + 2}px`
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
