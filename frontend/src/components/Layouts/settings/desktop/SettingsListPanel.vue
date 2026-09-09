<template>
	<SettingsFieldsPanel
		v-if="detailFields"
		:page="detailFields"
		:title="detailTitle"
		show-back
		@back="closeDetail"
		@renamed="recordRenamed"
	/>

	<component
		:is="detailComponent"
		v-else-if="detailComponent"
		:name="record"
		@back="closeDetail"
		@renamed="recordRenamed"
	/>

	<SettingsList
		v-else
		v-model:search="list.search"
		:title="title"
		:columns="page.columns"
		:rows="list.rows"
		:row-key="page.resource.rowKey"
		:loading="list.loading"
		:has-next-page="list.hasNextPage"
		:searchable="page.searchable"
		:show-new="Boolean(page.create)"
		:new-label="page.create?.label"
		:empty-name="page.empty?.name"
		:empty-icon="page.empty?.icon"
		flush
		@new="openCreate"
		@load-more="list.loadMore()"
		@row-click="openRow"
	>
		<template v-if="page.filter" #header-bottom>
			<Select
				v-model="filterValue"
				class="w-40"
				:aria-label="page.filter.ariaLabel()"
				:options="page.filter.options()"
			/>
		</template>
	</SettingsList>
</template>

<script lang="ts">
import type { ListPage, SelectOption } from '@/types/settingsSchema'
import type { SettingsListRow } from '@/types'
import type { SettingsListFilters } from '@/composables/useSettingsListResource'

/**
 * A single-choice narrowing of the list, drawn beside the search box.
 *
 * A method-backed list reads the value as a request parameter — get_members
 * takes `role` alongside `search` and `start`. A doctype list has no such
 * argument, so it declares `filters` as well and the value is mapped to
 * get_list filters instead.
 *
 * Every string is produced by a call, never a plain property: `__` is installed
 * on window after the settings tree has been imported, so a config module that
 * built these at module scope would call an undefined global.
 */
export interface ListPanelFilter {
	/** The request parameter this filter contributes. */
	name: string
	/** The value standing for "everything", and what the list opens on. */
	default: string
	ariaLabel: () => string
	options: () => SelectOption[]
	/**
	 * Maps the chosen value to get_list filters, for a doctype-backed list.
	 * Return nothing for the default value. Declaring it on a method-backed
	 * page has no effect — there is no resource to hand filters to.
	 */
	filters?: (value: string) => SettingsListFilters
}

/**
 * A `ListPage` plus the two things the shared schema cannot say yet.
 *
 * Both belong on `ListPage` in types/settingsSchema.ts; they are declared here
 * because this panel is what reads them, and a config module that carries one
 * still types as the `ListPage` the settings tree takes.
 */
export interface ListPanelPage extends ListPage {
	filter?: ListPanelFilter
	/**
	 * What a row click does INSTEAD of opening `rowDetail`.
	 *
	 * Users has both: a member's profile is a page of its own, so the row leaves
	 * settings entirely, while the record sub-page is reached from the row menu.
	 * Without this the two would have to be the same destination.
	 */
	rowClick?: (row: SettingsListRow) => void
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Select } from 'frappe-ui'
import SettingsFieldsPanel from '@/components/Layouts/settings/desktop/SettingsFieldsPanel.vue'
import SettingsList from '@/components/Layouts/settings/desktop/SettingsList.vue'
import {
	useSettingsListResource,
	useSettingsMethodResource,
	type SettingsListSource,
	type SettingsListView,
} from '@/composables/useSettingsListResource'
import type {
	DetailPage,
	FieldsPage,
	SettingsSource,
} from '@/types/settingsSchema'

// A `kind: 'list'` page, rendered whole: the list, the New affordance, and the
// detail that replaces the list when a record is open. Every list panel behaved
// this way already — ZoomSettings, Badges and EmailConfig each kept a `view` or
// `step` ref and swapped the form in for the list — so the behaviour lives here
// once and a panel becomes a `ListPage` object with no component of its own.
const props = defineProps<{
	page: ListPanelPage
	title: string
}>()

// The create id reserved by the settings hash ('#settings/<slug>/new'), so a
// record model driven from the URL and one driven from a click agree.
const NEW_RECORD = 'new'

// The open record, as a model rather than internal state: the URL layer drives
// this from the hash's second segment, and nothing else here knows about hashes.
const record = defineModel<string | null>('record', { default: null })

// Not `record.value = name`. The record model is the URL, and writing to it
// PUSHES a history entry — a rename is not somewhere the user navigated to, and
// Back from the renamed record has to land on the list rather than on the same
// record under its dead name. The page above owns the hash and replaces it.
const emit = defineEmits<{ renamed: [string] }>()

// The filter's own value, held here rather than in the config module: the
// config is a module-level constant shared by every mount, and a value written
// into it would be waiting in the next panel that opened.
const filterValue = ref(props.page.filter?.default ?? '')

const filterParams = (): Record<string, unknown> =>
	props.page.filter ? { [props.page.filter.name]: filterValue.value } : {}

// Read once, at setup. `createListResource` fixes its doctype and fields at
// creation, so a caller that renders two different ListPages through this
// component must key it per item or the second would keep the first's resource.
//
// A `method` names a whitelisted endpoint that returns the rows itself, which
// is not something a list resource can be talked into: it builds a get_list
// call out of a doctype and fields. Users is one — get_members applies its own
// filters and looks up each row's roles — so it pages against `start` instead.
const listSource = props.page.resource

// Read once, at setup, and kept: `filters` on a config can be a getter, and the
// resource was built from whatever it returned then. Re-reading it later would
// scope the list by a different answer than the rows on screen came from.
const scopeFilters = listSource.filters

// Held apart from `list` because only the doctype branch can be handed filters.
const doctypeList: SettingsListSource | null = listSource.method
	? null
	: useSettingsListResource({
			doctype: listSource.doctype,
			fields: listSource.fields,
			filters: scopeFilters,
			orderBy: listSource.orderBy,
			searchFields: listSource.searchFields,
	  })

const list: SettingsListView =
	doctypeList ??
	useSettingsMethodResource({
		method: listSource.method as string,
		doctype: listSource.doctype,
		// A catalogue endpoint returns the whole list in one answer and takes
		// no `start`, so paging it is meaningless — and worse than
		// meaningless: `hasNextPage` is `data.length >= pageLength`, so a
		// catalogue at or above the default 13 draws a Load More that refetches
		// the same rows and appends every one of them a second time.
		pageLength: listSource.pageLength,
		params: filterParams,
	})

const asTriples = (filters: SettingsListFilters): any[][] =>
	Array.isArray(filters)
		? filters
		: Object.entries(filters).map(([field, value]) =>
				Array.isArray(value) ? [field, value[0], value[1]] : [field, '=', value]
		  )

// The page's own filters are a scope, not a default: Google Meet holds a
// non-moderator to their own row that way. `applyFilters` replaces outright, so
// the scope has to be sent again underneath every chosen value.
const mergeFilters = (
	scope: SettingsListFilters | undefined,
	chosen: SettingsListFilters
): SettingsListFilters => {
	if (!scope) return chosen
	if (!Array.isArray(scope) && !Array.isArray(chosen))
		return { ...scope, ...chosen }
	return [...asTriples(scope), ...asTriples(chosen)]
}

// Back to the first page, the way a search is: the filter goes to the server,
// so what is on screen was fetched under the old one and none of it can be kept.
watch(filterValue, (value) => {
	const toFilters = props.page.filter?.filters
	if (doctypeList && toFilters)
		return doctypeList.applyFilters(
			mergeFilters(scopeFilters, toFilters(value))
		)
	return list.reload()
})

// The row behind the open record is found by name and the detail's header is
// drawn from it, so a list still holding the old name shows the old name — and
// once the record model follows the rename, no row matches at all and the
// header falls back to the page's generic title.
const recordRenamed = (name: string) => {
	emit('renamed', name)
	list.reload()
}

const detail = computed<DetailPage | null>(() => {
	if (!record.value) return null
	if (record.value === NEW_RECORD) return props.page.create?.detail ?? null
	return props.page.rowDetail ?? null
})

// The row behind the open record, for the detail's title. A create form has no
// row, and a deep link can name a record on a page the list has not reached, so
// the title function has to survive being handed nothing.
const detailRow = computed<SettingsListRow>(() => {
	if (!record.value || record.value === NEW_RECORD) return {}
	return list.rows.find((row) => row.name === record.value) ?? {}
})

// `record: 'route'` says the record is whichever one the URL names; that value
// is the record model here, so the fields page is handed a concrete name and
// never has to know how the page was reached. A create form has no name yet —
// the empty name is what makes the write an insert.
const resolveSource = (source: SettingsSource): SettingsSource => {
	if (!('record' in source)) return source
	return {
		doctype: source.doctype,
		name: record.value === NEW_RECORD ? '' : record.value ?? '',
	}
}

// The spread carries `title` and `enabledField` through untouched. Both belong
// to whoever owns the document and the header, which for a fields detail is
// SettingsFieldsPanel — it renders its own SettingsLayout, so the enabled toggle
// cannot be hoisted from out here.
const detailFields = computed<FieldsPage | null>(() => {
	const page = detail.value
	if (!page || page.kind !== 'fields') return null
	return { ...page, source: resolveSource(page.source) }
})

const detailComponent = computed(() =>
	detail.value?.kind === 'custom' ? detail.value.component : null
)

const detailTitle = computed(() => {
	const page = detail.value
	return page && page.kind === 'fields' ? page.title(detailRow.value) : ''
})

const openCreate = () => {
	record.value = NEW_RECORD
}

// A page that says where its rows go is obeyed, whether or not it also has a
// record sub-page: Users has both, and a click on a member is a click on the
// person, not on their settings record.
const openRow = (row: SettingsListRow) => {
	if (props.page.rowClick) return props.page.rowClick(row)
	if (props.page.rowDetail) record.value = row.name
}

// A detail owns its own writes and reports only that it is finished, so a save
// and a delete both reach the list as a close. Reloading here is what keeps a
// renamed or removed row from lingering.
const closeDetail = () => {
	record.value = null
	list.reload()
}
</script>
