<template>
	<SettingsList
		v-if="!record"
		:title="label"
		:columns="couponColumns"
		:rows="list.rows"
		:loading="list.loading"
		:has-next-page="list.hasNextPage"
		v-model:search="list.search"
		searchable
		empty-name="Coupons"
		empty-icon="lucide-ticket"
		@new="openForm(NEW_RECORD)"
		@load-more="list.loadMore()"
		@row-click="(row) => openForm(row.name)"
	/>

	<CouponForm v-else :name="record" @back="closeForm()" />
</template>
<script setup lang="ts">
import { useSettingsListResource } from '@/composables/useSettingsListResource'
import { NEW_RECORD } from '@/composables/useSettingsSource'
import CouponForm from '@/components/Settings/Coupons/CouponForm.vue'
import SettingsList from '@/components/Layouts/settings/desktop/SettingsList.vue'
import {
	couponColumns,
	couponListOptions,
} from '@/components/Settings/Coupons/coupons'

// The list of one settings page, and the form behind a row as its own
// component. CouponForm is imported statically rather than as an async
// component, because a row click reveals the form on the same tick.

defineProps<{
	label: string
}>()

// The open record, as a model rather than state of its own, which is the same
// contract SettingsListPanel has. Whether the form is showing is read off this
// and never stored beside it, because a second copy could disagree with the URL.
const record = defineModel<string | null>('record', { default: null })

const list = useSettingsListResource(couponListOptions)

const openForm = (name: string) => {
	record.value = name
}

const closeForm = () => {
	record.value = null
}
</script>
