<template>
	<SettingsList
		v-if="view === 'list'"
		v-model:search="list.search"
		:title="__(label)"
		:columns="templateColumns"
		:rows="list.rows"
		:loading="list.loading"
		:has-next-page="list.hasNextPage"
		searchable
		empty-name="Email Templates"
		empty-icon="lucide-mail-plus"
		@new="openForm(null)"
		@load-more="list.loadMore()"
		@row-click="openForm"
	/>

	<EmailTemplateForm v-else :name="selected" @back="closeForm()" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import EmailTemplateForm from '@/components/Settings/EmailTemplate/EmailTemplateForm.vue'
import SettingsList from '@/components/Layouts/settings/desktop/SettingsList.vue'
import {
	DOCTYPE,
	TEMPLATE_FIELDS,
	TEMPLATE_ORDER_BY,
	TEMPLATE_SEARCH_FIELDS,
	templateColumns,
} from '@/components/Settings/EmailTemplate/emailTemplates'
import { useSettingsListResource } from '@/composables/useSettingsListResource'
import { NEW_RECORD } from '@/composables/useSettingsSource'
import type { SettingsListRow } from '@/types'

// Settings > Templates: the list, with the record behind New and a row in
// EmailTemplateForm.vue. Three files per list page — the config, this list,
// the form — and the form is imported statically so a row click reveals it on
// the same tick.

defineProps<{ label: string }>()

const view = ref<'list' | 'form'>('list')

const list = useSettingsListResource<SettingsListRow>({
	doctype: DOCTYPE,
	// Duplicate copies the body, so the list has to have fetched it.
	fields: TEMPLATE_FIELDS,
	searchFields: TEMPLATE_SEARCH_FIELDS,
	orderBy: TEMPLATE_ORDER_BY,
})

// The record the form is on: a template name, or NEW_RECORD.
const selected = ref<string | null>(null)

const openForm = (row: SettingsListRow | null) => {
	selected.value = row ? String(row.name) : NEW_RECORD
	view.value = 'form'
}

// The list is refetched rather than trusted: a rename moved a row's name and a
// save moved its subject, and neither reached the rows already on screen.
const closeForm = () => {
	view.value = 'list'
	selected.value = null
	list.reload()
}
</script>
