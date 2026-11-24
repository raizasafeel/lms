<template>
	<div
		class="grid w-full items-start gap-x-12 gap-y-10 px-5 py-8"
		:class="{ '@4xl:grid-cols-[minmax(0,1fr)_minmax(0,16rem)]': !flowDocked }"
	>
		<div class="min-w-0 space-y-10">
			<slot />
		</div>
		<aside
			v-if="!flowDocked"
			class="hidden @4xl:sticky @4xl:top-[calc(var(--header-frame-h)+1.25rem)] @4xl:block"
		>
			<SettingsSectionNav
				:sections="sections"
				:active="active"
				@select="goTo"
			/>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, provide, ref, shallowRef } from 'vue'
import SettingsSectionNav from '@/components/InlineEdit/SettingsSectionNav.vue'
import { useFlowDocked } from '@/composables/useFlowDocked'
import {
	SETTINGS_SECTIONS,
	inPageOrder,
	type SettingsSection,
} from '@/components/InlineEdit/settingsSections'

/** A settings tab: its sections in one column, a nav of them beside it from lg. */
// With Flow docked beside the app, one more panel is too many.
const flowDocked = useFlowDocked()
const sections = shallowRef<SettingsSection[]>([])
const active = ref<string | null>(null)
const inView = new Set<string>()

// A section counts as in view while it crosses the band below the header.
// Absent outside a browser, where the nav simply marks the section picked.
const observer =
	'IntersectionObserver' in window
		? new IntersectionObserver(onIntersect, {
				rootMargin: '-80px 0px -60% 0px',
		  })
		: null

function onIntersect(entries: IntersectionObserverEntry[]): void {
	for (const entry of entries) {
		if (entry.isIntersecting) inView.add(entry.target.id)
		else inView.delete(entry.target.id)
	}
	const first = sections.value.find((section) => inView.has(section.id))
	if (first) active.value = first.id
}

function goTo(section: SettingsSection): void {
	active.value = section.id
	// The first section goes to the very top, tabs and all, as on arrival.
	if (section.id === sections.value[0]?.id) {
		scrollParent(section.element)?.scrollTo({ top: 0, behavior: 'smooth' })
		return
	}
	section.element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function scrollParent(element: HTMLElement): HTMLElement | null {
	let node = element.parentElement
	while (node && !/(auto|scroll)/.test(getComputedStyle(node).overflowY)) {
		node = node.parentElement
	}
	return node
}

provide(SETTINGS_SECTIONS, {
	register(section) {
		sections.value = inPageOrder([...sections.value, section])
		active.value ??= sections.value[0].id
		observer?.observe(section.element)
	},
	unregister(id) {
		const section = sections.value.find((current) => current.id === id)
		if (section) observer?.unobserve(section.element)
		sections.value = sections.value.filter((current) => current.id !== id)
		inView.delete(id)
	},
})

onBeforeUnmount(() => observer?.disconnect())
</script>
