<template>
	<section :id="id" ref="section" class="scroll-mt-6 space-y-1">
		<h2
			class="border-b border-outline-gray-2 pb-3 text-lg-semibold text-ink-gray-9"
		>
			{{ title }}
		</h2>
		<div class="divide-y divide-outline-gray-1">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
import { inject, onBeforeUnmount, onMounted, useId, useTemplateRef } from 'vue'
import { SETTINGS_SECTIONS } from '@/components/InlineEdit/settingsSections'

/** A titled settings section, its rows split by hairlines. */
const props = defineProps<{
	title: string
	/** Its icon in the page's section nav. */
	icon?: string
}>()

const id = useId()
const section = useTemplateRef<HTMLElement>('section')
const sections = inject(SETTINGS_SECTIONS, null)

onMounted(() =>
	sections?.register({
		id,
		title: props.title,
		icon: props.icon,
		element: section.value!,
	})
)
onBeforeUnmount(() => sections?.unregister(id))
</script>
