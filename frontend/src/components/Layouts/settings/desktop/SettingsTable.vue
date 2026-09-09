<template>
	<div
		class="-mx-3 min-h-0 flex-1 overflow-y-auto [--list-row-height:3.5rem]"
		:style="scrollerStyle"
	>
		<List :columns="tracks" class="list-row-px-3">
			<ListHeader class="sticky top-0 z-10 bg-surface-elevation-1">
				<ListHeaderCell
					v-for="column in columns"
					:key="column.key"
					class="text-p-sm"
				>
					{{ column.label }}
				</ListHeaderCell>
			</ListHeader>
			<div role="rowgroup">
				<ListRows :items="rows" :row-key="rowKey" v-slot="{ item: row }">
					<ListRow
						class="dark:sm:hover:bg-surface-gray-2 [outline-offset:-3px]"
						@click="emit('rowClick', row)"
					>
						<ListCell
							v-for="column in columns"
							:key="column.key"
							:class="
								column.type === 'text' ? 'text-p-base text-ink-gray-6' : ''
							"
							@click="stopWhenInteractive(column, $event)"
						>
							<slot name="cell" :column="column" :row="row">
								<template v-if="column.type === 'stacked'">
									<Avatar
										v-if="column.avatar"
										v-bind="column.avatar(row)"
										size="xl"
										class="me-3 shrink-0"
									/>
									<span v-else-if="column.leading" class="me-3 shrink-0">
										<slot name="leading" :column="column" :row="row" />
									</span>
									<div class="flex min-w-0 flex-col">
										<span class="truncate text-p-base text-ink-gray-8">
											{{ column.primary(row) }}
										</span>
										<span
											v-if="column.secondary"
											class="truncate text-p-sm text-ink-gray-5"
										>
											{{ column.secondary(row) }}
										</span>
									</div>
									<Badge
										v-if="rowStatus?.(row)"
										theme="orange"
										class="ms-2 shrink-0"
									>
										{{ rowStatus(row) }}
									</Badge>
								</template>

								<template v-else-if="column.type === 'text'">
									<Avatar
										v-if="column.avatar"
										v-bind="column.avatar(row)"
										size="lg"
										class="me-3 shrink-0"
									/>
									<span class="truncate">{{ column.value(row) }}</span>
								</template>

								<template v-else-if="column.type === 'badge'">
									<div class="flex min-w-0 items-center gap-2 overflow-hidden">
										<Badge
											v-for="badge in visibleBadges(column, row)"
											:key="badge.label"
											:theme="badge.theme || 'gray'"
											class="shrink-0"
										>
											{{ badge.label }}
										</Badge>
									</div>
									<template v-if="hiddenBadges(column, row).length">
										<span
											class="ms-2 inline-flex h-5 shrink-0 items-center rounded-full bg-surface-gray-3 px-1.5 text-xs-medium text-ink-gray-7"
											:title="hiddenBadgeSummary(column, row)"
											aria-hidden="true"
										>
											+{{ hiddenBadges(column, row).length }}
										</span>
										<span class="sr-only">
											{{ hiddenBadgeSummary(column, row) }}
										</span>
									</template>
								</template>

								<Switch
									v-else-if="column.type === 'switch'"
									size="sm"
									:model-value="column.checked(row)"
									:disabled="column.disabled ? column.disabled(row) : false"
									@update:model-value="(value: boolean) => column.onChange(row, value)"
								>
									<template #label>
										<span class="sr-only">{{ column.ariaLabel(row) }}</span>
									</template>
								</Switch>

								<Dropdown
									v-else-if="
										column.type === 'actions' && column.options(row).length
									"
									:options="column.options(row)"
									:button="{
										icon: 'lucide-more-horizontal',
										variant: 'ghost',
										label: column.ariaLabel
											? column.ariaLabel(row)
											: __('More options'),
									}"
									placement="right"
								/>
							</slot>
						</ListCell>
					</ListRow>
				</ListRows>
			</div>
		</List>

		<div v-if="hasNextPage" class="mt-4 flex justify-center">
			<Button @click="emit('loadMore')">
				<template #prefix>
					<span class="lucide-refresh-cw size-3" />
				</template>
				{{ __('Load More') }}
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
// The rows of a settings list, without the page around them. A panel declares
// columns and never writes cell markup, so every settings table reads the same
// way, whether it is the whole page or a tab inside one.

// Header and rows are separate grid containers over one `--list-columns` track
// list, and they must share the same scroller, or a classic scrollbar narrows
// the rows and every fixed column after the `fr` track lands 15px off.

// Load More is inside the scroller because it is the row after the last row,
// and outside the List because `List` is a `role="table"` that owns only rows.
// The dark hover wash wins on source order, so reordering the variants undoes it.
import { computed } from 'vue'
import { Avatar, Badge, Button, Dropdown, Switch } from 'frappe-ui'
import {
	List,
	ListCell,
	ListHeader,
	ListHeaderCell,
	ListRow,
	ListRows,
} from 'frappe-ui/list'
import type {
	BadgeColumn,
	SettingsListBadge,
	SettingsListColumn,
	SettingsListRow,
} from '@/types'

const props = withDefaults(
	defineProps<{
		columns: SettingsListColumn[]
		rows: SettingsListRow[]
		rowKey?: string
		hasNextPage?: boolean
		/** A word for a row that is not syncing, badged beside its name. Null when it is. */
		rowStatus?: (row: SettingsListRow) => string | null
		/**
		 * Fix the scrolling area to this many rows, instead of letting it fill the
		 * room its page gives it. Opt-in, because a panel that IS its page should
		 * use the height it has.
		 */
		visibleRows?: number
	}>(),
	{
		rowKey: 'name',
		hasNextPage: false,
		rowStatus: undefined,
		visibleRows: undefined,
	}
)

// A ceiling, not a fixed height, because a hard height clips on a short
// viewport. An inline style, because the row height is a custom property and a
// class assembled from a prop is what the JIT scan cannot see.
const scrollerStyle = computed(() =>
	props.visibleRows
		? {
				maxHeight: `calc(var(--list-row-height) * ${props.visibleRows} + 2rem)`,
		  }
		: undefined
)

const emit = defineEmits<{
	rowClick: [row: SettingsListRow]
	loadMore: []
}>()

const tracks = computed(() =>
	props.columns.map((column) => {
		if (column.width) return column.width
		return column.type === 'actions' ? '2.25rem' : 'minmax(0, 1fr)'
	})
)

// Badges are bounded by counting, not clipping. They are flex items whose
// automatic minimum size is their own label, so they refuse to shrink and paint
// out of the cell. Past the limit they collapse into a `+N`.
const DEFAULT_MAX_BADGES = 3

const badgeLimit = (column: BadgeColumn): number =>
	column.maxBadges ?? DEFAULT_MAX_BADGES

const visibleBadges = (
	column: BadgeColumn,
	row: SettingsListRow
): SettingsListBadge[] => column.badges(row).slice(0, badgeLimit(column))

const hiddenBadges = (
	column: BadgeColumn,
	row: SettingsListRow
): SettingsListBadge[] => column.badges(row).slice(badgeLimit(column))

// What the `+N` stands for, as text. A bare number tells a screen reader
// nothing, `title` is not reachable from the keyboard, and the row is already a
// button, so a tooltip trigger inside it would nest one control in another.
const hiddenBadgeSummary = (
	column: BadgeColumn,
	row: SettingsListRow
): string => {
	const hidden = hiddenBadges(column, row)
	return __('and {0} more: {1}').format(
		String(hidden.length),
		hidden.map((badge) => badge.label).join(', ')
	)
}

// A cell the user operates is not also a cell that opens the row.
const stopWhenInteractive = (column: SettingsListColumn, event: Event) => {
	if (column.type === 'switch' || column.type === 'actions')
		event.stopPropagation()
}
</script>
