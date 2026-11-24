<template>
	<div class="flex flex-col gap-2">
		<FormControl
			v-model="query"
			type="text"
			:placeholder="__('Search icons')"
			:aria-label="__('Search icons')"
			@keydown.down.prevent="focusGrid"
		>
			<template #prefix>
				<span class="lucide-search size-4 text-ink-gray-5" />
			</template>
		</FormControl>
		<div ref="scroller" class="h-56 overflow-y-auto">
			<div
				ref="grid"
				class="grid gap-1.5"
				:class="GRID_COLUMNS[columns]"
				role="group"
				:aria-label="__('Thumbnail icon')"
				@keydown="moveFocus"
			>
				<button
					v-for="name in visible"
					:key="name"
					type="button"
					class="flex h-9 items-center justify-center rounded-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
					:class="
						isPicked(name)
							? 'bg-surface-gray-3 text-ink-gray-9'
							: 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8'
					"
					:tabindex="name === focusable ? 0 : -1"
					:aria-label="name.replace(/-/g, ' ')"
					:aria-pressed="isPicked(name)"
					@click="icon = name"
				>
					<span :class="[courseIcon(name), 'size-4']" aria-hidden="true" />
				</button>
			</div>
			<p
				v-if="!visible.length"
				class="py-6 text-center text-p-sm text-ink-gray-6"
			>
				{{ __('No icons match') }}
			</p>
			<div ref="sentinel" class="h-px" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { useIntersectionObserver } from '@vueuse/core'
import { COURSE_ICONS, courseIcon } from '@/utils/courseIcons'
import { loadIconTags } from '@/utils/lucideIconStyles'

/** Any lucide icon for a course thumbnail: curated first, searchable by name or keyword. */
const GRID_COLUMNS = {
	6: 'grid-cols-6',
	12: 'grid-cols-12',
	16: 'grid-cols-[repeat(16,minmax(0,1fr))]',
} as const

const props = withDefaults(defineProps<{ columns?: 6 | 12 | 16 }>(), {
	columns: 6,
})

const icon = defineModel<string | null | undefined>()

const PAGE = 108
const query = ref('')
const limit = ref(PAGE)
const tags = shallowRef<Record<string, string[]>>({})
const scroller = ref<HTMLElement>()
const grid = ref<HTMLElement>()
const sentinel = ref<HTMLElement>()

// Read once, so picking an icon never reorders the grid under the pointer.
const opening = courseIcon(icon.value).replace(/^lucide-/, '')

const first = COURSE_ICONS.includes(opening)
	? COURSE_ICONS
	: [opening, ...COURSE_ICONS]

const ordered = computed(() => [
	...first,
	...Object.keys(tags.value).filter((name) => !first.includes(name)),
])

function matches(name: string, term: string): boolean {
	return (
		name.replace(/-/g, ' ').includes(term) ||
		(tags.value[name] || []).some((tag) => tag.includes(term))
	)
}

const results = computed(() => {
	const term = query.value.trim().toLowerCase().replace(/-/g, ' ')
	if (!term) return ordered.value
	return ordered.value.filter((name) => matches(name, term))
})

const visible = computed(() => results.value.slice(0, limit.value))

const current = computed(() => courseIcon(icon.value))
const isPicked = (name: string): boolean => current.value === `lucide-${name}`

const focusable = computed(
	() => visible.value.find(isPicked) || visible.value[0]
)

onMounted(async () => {
	tags.value = await loadIconTags()
})

watch(query, () => {
	limit.value = PAGE
	scroller.value?.scrollTo?.({ top: 0 })
})

useIntersectionObserver(
	sentinel,
	([entry]) => {
		if (entry?.isIntersecting && limit.value < results.value.length)
			limit.value += PAGE
	},
	{ root: scroller }
)

function focusGrid(): void {
	grid.value?.querySelector<HTMLElement>('[tabindex="0"]')?.focus()
}

function nextIndex(key: string, from: number, count: number): number | null {
	const steps: Record<string, number> = {
		ArrowLeft: -1,
		ArrowRight: 1,
		ArrowUp: -props.columns,
		ArrowDown: props.columns,
	}
	if (key === 'Home') return 0
	if (key === 'End') return count - 1
	if (!(key in steps)) return null
	return Math.min(Math.max(from + steps[key], 0), count - 1)
}

function moveFocus(event: KeyboardEvent): void {
	const buttons = [...(grid.value?.querySelectorAll('button') || [])]
	const from = buttons.indexOf(event.target as HTMLButtonElement)
	const to = nextIndex(event.key, from, buttons.length)
	if (from < 0 || to === null) return
	event.preventDefault()
	buttons[to].focus()
}
</script>
