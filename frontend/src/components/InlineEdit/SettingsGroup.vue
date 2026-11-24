<template>
	<section :id="id" ref="section" class="scroll-mt-6 space-y-2">
		<div class="flex items-center gap-1.5">
			<h2 class="text-lg-semibold text-ink-gray-9">{{ title }}</h2>
			<Tooltip v-if="info" :text="info">
				<button
					type="button"
					class="flex text-ink-gray-5 hover:text-ink-gray-7"
					:aria-label="info"
				>
					<span class="lucide-info size-4" aria-hidden="true" />
				</button>
			</Tooltip>
		</div>
		<div class="divide-y divide-outline-gray-1">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { inject, onBeforeUnmount, onMounted, useId, useTemplateRef } from 'vue'
import { SETTINGS_SECTIONS } from '@/components/InlineEdit/settingsSections'

/** A titled settings section, its rows split by hairlines. */
const props = defineProps<{
	title: string
	/** Its icon in the page's section nav. */
	icon?: string
	/** A stable name a link can point at with `?section=`. */
	name?: string
	/** What the section is for, behind an (i) next to the title. */
	info?: string
}>()

const id = props.name ? `settings-${props.name}` : useId()
const section = useTemplateRef<HTMLElement>('section')
const sections = inject(SETTINGS_SECTIONS, null)

onMounted(() =>
	sections?.register({
		id,
		title: props.title,
		icon: props.icon,
		name: props.name,
		element: section.value!,
	})
)
onBeforeUnmount(() => sections?.unregister(id))
</script>
