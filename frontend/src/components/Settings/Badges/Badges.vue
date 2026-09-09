<template>
	<SettingsList
		v-if="!record"
		:title="__(label)"
		:columns="columns"
		:rows="list.rows"
		:loading="list.loading"
		:has-next-page="list.hasNextPage"
		v-model:search="list.search"
		searchable
		:search-label="__('Search badges')"
		empty-name="Badges"
		empty-icon="lucide-award"
		@new="openForm(null)"
		@load-more="list.loadMore()"
		@row-click="openForm"
	/>

	<BadgeForm v-else :name="record" :row="selectedRow" @back="closeForm()" />
</template>

<script setup lang="ts">
import { call, toast } from 'frappe-ui'
import { computed } from 'vue'
import BadgeForm from '@/components/Settings/Badges/BadgeForm.vue'
import SettingsList from '@/components/Layouts/settings/desktop/SettingsList.vue'
import {
	BADGE_DOCTYPE,
	BADGE_FIELDS,
	BADGE_SEARCH_FIELDS,
	badgeColumns,
} from '@/components/Settings/Badges/badges'
import { useSettingsListResource } from '@/composables/useSettingsListResource'
import { NEW_RECORD } from '@/composables/useSettingsSource'
import { cleanError } from '@/utils'
import type { Badge, SettingsListRow } from '@/types'

// Settings > Badges: the list, with the badge behind New and behind a row in
// BadgeForm.vue. Three files per list page — the config, this list, the form —
// and the form is imported statically so a row click reveals it on the same
// tick.

defineProps<{ label: string }>()

// The open record, as a model rather than state of its own — the same contract
// SettingsListPanel has, and what makes '#settings/badges/<name>' land on that
// badge. Whether the form is showing is read off this and never stored beside
// it: a second copy could disagree with the URL, and a derived one cannot.
const record = defineModel<string | null>('record', { default: null })

const list = useSettingsListResource<Badge>({
	doctype: BADGE_DOCTYPE,
	fields: BADGE_FIELDS,
	searchFields: BADGE_SEARCH_FIELDS,
	orderBy: 'creation desc',
})

// The row behind the open record, so the header can name the badge before its
// document lands. Looked up rather than remembered from the click: a deep link
// arrives with no click behind it, and a create form has no row at all.
const selectedRow = computed<SettingsListRow | null>(() => {
	if (!record.value || record.value === NEW_RECORD) return null
	return list.rows.find((row) => row.name === record.value) ?? null
})

// Written straight through, and the row moved first so the switch answers the
// press rather than the round trip. A refused write puts the row back.
const toggleEnabled = async (row: SettingsListRow, value: boolean) => {
	const previous = row.enabled
	row.enabled = value
	try {
		await call('frappe.client.set_value', {
			doctype: BADGE_DOCTYPE,
			name: row.name,
			fieldname: 'enabled',
			value: value ? 1 : 0,
		})
	} catch (err: any) {
		row.enabled = previous
		toast.error(cleanError(err?.messages?.[0]) || __('Error updating badge'))
	}
}

const deleteBadge = (row: SettingsListRow) => {
	list.remove(String(row.name), {
		onSuccess: () => toast.success(__('Badge deleted successfully')),
		onError: (err) =>
			toast.error(cleanError(err.messages?.[0]) || __('Error deleting badge')),
	})
}

const columns = badgeColumns({ toggleEnabled, remove: deleteBadge })

const openForm = (row: SettingsListRow | null) => {
	record.value = row ? String(row.name) : NEW_RECORD
}

const closeForm = () => {
	record.value = null
	list.reload()
}
</script>
