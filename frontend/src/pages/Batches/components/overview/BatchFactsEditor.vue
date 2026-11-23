<template>
	<div class="space-y-2.5 text-p-base text-ink-gray-8">
		<div class="flex items-center gap-2.5 rounded-4" :class="ring('dates')">
			<span class="lucide-calendar size-4 shrink-0 text-ink-gray-5" />
			<DateRangePicker
				v-model="dates"
				variant="outline"
				format="D MMM YYYY"
				:placeholder="__('Start and end dates')"
				:aria-label="__('Batch dates')"
				class="flex-1"
			/>
		</div>
		<div class="flex items-center gap-2.5 rounded-4" :class="ring('times')">
			<span class="lucide-clock size-4 shrink-0 text-ink-gray-5" />
			<TimePicker
				v-model="doc.start_time"
				variant="outline"
				format="h:mm a"
				:interval="30"
				:placeholder="__('Start')"
				:aria-label="__('Class start time')"
				class="w-28"
			/>
			<span class="text-ink-gray-6">–</span>
			<TimePicker
				v-model="doc.end_time"
				variant="outline"
				format="h:mm a"
				:interval="30"
				:placeholder="__('End')"
				:aria-label="__('Class end time')"
				class="w-28"
			/>
		</div>
		<div class="flex items-center gap-2.5 rounded-4" :class="ring('timezone')">
			<span class="lucide-globe size-4 shrink-0 text-ink-gray-5" />
			<Combobox
				v-model="doc.timezone"
				:options="timezoneOptions"
				:placeholder="__('Timezone')"
				:aria-label="__('Timezone')"
				variant="outline"
				class="flex-1"
			/>
		</div>
		<div class="flex items-center gap-2.5">
			<span
				class="size-4 shrink-0 text-ink-gray-5"
				:class="doc.medium === 'Offline' ? 'lucide-map-pin' : 'lucide-video'"
			/>
			<Select
				:modelValue="doc.medium === 'Offline' ? 'Offline' : 'Online'"
				:options="mediumOptions"
				variant="outline"
				:aria-label="__('Medium')"
				class="w-36"
				@update:modelValue="(value) => (doc.medium = value as LMSBatch['medium'])"
			/>
		</div>
		<div class="flex items-center gap-2.5">
			<span class="lucide-armchair size-4 shrink-0 text-ink-gray-5" />
			<FormControl
				:modelValue="doc.seat_count || ''"
				type="number"
				min="1"
				variant="outline"
				placeholder="–"
				:aria-label="__('Seat count')"
				class="w-20"
				@update:modelValue="
					(value: string) => (doc.seat_count = Number(value) || 0)
				"
			/>
			<span class="text-ink-gray-6">
				{{ doc.seat_count ? __('seats') : __('No seat limit') }}
			</span>
		</div>
		<BatchSwitchFact
			v-model="doc.certification"
			icon="lucide-badge-check"
			:on="__('Certificate')"
			:off="__('No certificate')"
		/>
		<BatchSwitchFact
			v-model="doc.evaluation"
			icon="lucide-user-check"
			:on="__('1-on-1 evaluation')"
			:off="__('No evaluation')"
		/>
		<div v-if="doc.evaluation" class="flex items-center gap-2 ps-[1.625rem]">
			<span class="shrink-0 text-p-sm text-ink-gray-6">{{
				__('Book by')
			}}</span>
			<DatePicker
				v-model="doc.evaluation_end_date"
				variant="outline"
				format="D MMM YYYY"
				:min="doc.end_date"
				:placeholder="__('Evaluation end date')"
				class="flex-1"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
	Combobox,
	createResource,
	DatePicker,
	DateRangePicker,
	FormControl,
	Select,
	TimePicker,
} from 'frappe-ui'
import { missingRing } from '@/components/InlineEdit/fieldClasses'
import BatchSwitchFact from '@/pages/Batches/components/overview/BatchSwitchFact.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** The enrol card's facts as inline fields. */
const props = defineProps<{ doc: LMSBatch; form: BatchForm }>()

const ring = (key: string) => missingRing(props.form.isMissing(key))

const dates = computed<[string, string] | []>({
	get: () =>
		props.doc.start_date ? [props.doc.start_date, props.doc.end_date] : [],
	set: (range) => {
		props.doc.start_date = range[0] || ''
		props.doc.end_date = range[1] || ''
	},
})

const mediumOptions = [
	{ label: __('Online'), value: 'Online' },
	{ label: __('In person'), value: 'Offline' },
]

const timezones = createResource({
	url: 'frappe.geo.country_info.get_country_timezone_info',
	auto: true,
	cache: 'timezones',
	transform: (data: { all_timezones: string[] }) => data.all_timezones,
})

const timezoneOptions = computed(() =>
	((timezones.data as string[] | null) || []).map((zone) => ({
		label: zone,
		value: zone,
	}))
)
</script>
