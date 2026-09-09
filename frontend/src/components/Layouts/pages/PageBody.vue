<template>
	<div class="flex flex-1 flex-col sm:min-h-0">
		<div class="flex flex-1 flex-col sm:min-h-0 sm:overflow-y-auto">
			<div
				v-if="hasNameStrip"
				data-testid="page-header-block"
				class="mb-5 flex shrink-0 flex-col justify-between gap-4 border-b px-5 pb-4 pt-5 sm:border-b-0 sm:pb-0 md:flex-row md:items-center"
			>
				<div class="flex min-w-0 items-center justify-between gap-3">
					<h1 v-if="hasName" class="text-lg-semibold min-w-0 text-ink-gray-9">
						<slot name="name">{{ title }}</slot>
					</h1>
					<Button
						v-if="$slots.filters && isMobile"
						class="shrink-0"
						data-testid="mobile-filters-button"
						:aria-haspopup="'dialog'"
						:aria-expanded="showFilters"
						@click="showFilters = true"
					>
						<template #prefix>
							<span class="lucide-list-filter size-4" />
						</template>
						{{ __('Filters') }}
						<template v-if="activeFilters" #suffix>
							<span
								class="rounded-full bg-surface-gray-4 px-1.5 text-p-xs text-ink-gray-8"
							>
								{{ activeFilters }}
							</span>
						</template>
					</Button>
				</div>
				<div
					v-if="$slots.filters && !isMobile"
					class="flex flex-wrap items-center gap-3 [&>*]:w-full sm:[&>*]:w-44"
				>
					<slot name="filters" />
				</div>
			</div>

			<slot />
		</div>

		<BottomSheet
			v-if="$slots.filters && isMobile"
			v-model="showFilters"
			:title="__('Filters')"
		>
			<div
				data-testid="mobile-filters-sheet"
				class="flex flex-col gap-5 px-3 pb-2 [&>*]:w-full"
			>
				<slot name="filters" />
			</div>
		</BottomSheet>

		<div
			v-if="$slots.footer"
			class="z-10 mt-auto shrink-0 bg-surface-elevation-1 sm:static sm:mt-0"
			:class="unpinned ? '' : 'sticky bottom-0'"
		>
			<slot name="footer" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, useSlots } from 'vue'
import { Button } from 'frappe-ui'
import BottomSheet from '@/components/BottomSheet.vue'
import { useScreenSize } from '@/utils/composables'

// Filters on a phone were a row of chips, which past three or four is a wall of
// controls above the content the reader came for. Below `sm` they collapse to
// one Filters button beside the heading and open in a sheet.

// The slot is rendered in exactly one place rather than both with one hidden
// by CSS, because two renders would mount two copies of every control, each
// bound to the same page ref. `activeFilters` is optional and purely the badge.
const props = withDefaults(
	defineProps<{
		title?: string
		activeFilters?: number
		/**
		 * The page has a bulk selection open. On a phone its banner docks against
		 * the bottom edge this footer holds, so the footer travels with the rows.
		 * Left pinned, its controls would take focus out of sight under the banner.
		 */
		selecting?: boolean
	}>(),
	{ title: '', activeFilters: 0, selecting: false }
)

const slots = useSlots()
const { isMobile } = useScreenSize()
const showFilters = ref(false)

const unpinned = computed<boolean>(() => isMobile.value && props.selecting)

const hasName = computed<boolean>(() => Boolean(slots.name || props.title))

const hasNameStrip = computed<boolean>(() =>
	Boolean(hasName.value || slots.filters)
)
</script>
