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
		empty-name="Transactions"
		empty-icon="lucide-landmark"
		@new="openForm(NEW_RECORD)"
		@load-more="list.loadMore()"
		@row-click="(row) => openForm(row.name)"
	>
		<template #header-bottom>
			<Select
				v-model="status"
				data-testid="transaction-status"
				class="w-44"
				:aria-label="__('Filter by payment status')"
				:options="statusOptions()"
			/>
		</template>
	</SettingsList>

	<TransactionForm v-else :name="record" @back="closeForm()" />
</template>

<script setup lang="ts">
import { Select } from 'frappe-ui'
import { ref, watch } from 'vue'
import SettingsList from '@/components/Layouts/settings/desktop/SettingsList.vue'
import TransactionForm from '@/components/Settings/Transactions/TransactionForm.vue'
import {
	STATUS_ALL,
	columns,
	statusFilters,
	statusOptions,
	transactionList,
} from '@/components/Settings/Transactions/transactions'
import { useSettingsListResource } from '@/composables/useSettingsListResource'
import { NEW_RECORD } from '@/composables/useSettingsSource'

// Settings > Payment > Transactions: the list of payments, with the one payment
// behind a row or behind New in TransactionForm.vue. The form is imported
// statically so a row click reveals it on the same tick.

defineProps<{ label: string }>()

// The open record, as a model rather than state of its own, which is what makes
// '#settings/transactions/<name>' land on it. Whether the form is showing is read off
// this and never stored beside it.
const record = defineModel<string | null>('record', { default: null })

const list = useSettingsListResource(transactionList)

const status = ref(STATUS_ALL)

// Straight to the server, and back to the first page: the rows on screen were
// fetched under the old filter, so none of them can be kept.
watch(status, (value) => list.applyFilters(statusFilters(value)))

const openForm = (name: string) => {
	record.value = name
}

const closeForm = () => {
	record.value = null
	list.reload()
}
</script>
