<template>
	<div class="space-y-2.5 text-p-base text-ink-gray-8">
		<DateRangePicker
			v-model="dates"
			variant="ghost"
			format="D MMM YYYY"
			:placeholder="__('Start and end dates')"
			:aria-label="__('Batch dates')"
			class="w-full rounded-4"
			:class="ring('dates')"
		>
			<template #prefix>
				<span class="lucide-calendar size-4 text-ink-gray-5" />
			</template>
		</DateRangePicker>
		<TimeRangeField
			v-model:start="doc.start_time"
			v-model:end="doc.end_time"
			:startLabel="__('Class start time')"
			:endLabel="__('Class end time')"
			class="rounded-4"
			:class="ring('times')"
		/>
		<div>
			<Combobox
				v-model="doc.timezone"
				:options="timezoneOptions"
				:placeholder="__('Timezone')"
				:aria-label="__('Timezone')"
				variant="ghost"
				class="w-full rounded-4"
				:class="ring('timezone')"
			>
				<template #prefix>
					<span class="lucide-globe size-4 text-ink-gray-5" />
				</template>
			</Combobox>
		</div>
		<div class="grid grid-cols-2 gap-2">
			<Select
				:modelValue="doc.medium === 'Offline' ? 'Offline' : 'Online'"
				:options="mediumOptions"
				variant="ghost"
				:aria-label="__('Medium')"
				@update:modelValue="
					(value) => (doc.medium = value as LMSBatch['medium'])
				"
			>
				<template #prefix>
					<span
						class="size-4 text-ink-gray-5"
						:class="
							doc.medium === 'Offline' ? 'lucide-map-pin' : 'lucide-video'
						"
					/>
				</template>
			</Select>
		</div>
		<div class="grid grid-cols-2 items-center gap-2">
			<FormControl
				:modelValue="doc.seat_count || ''"
				type="number"
				min="1"
				variant="ghost"
				placeholder="–"
				:aria-label="__('Seat count')"
				@update:modelValue="
					(value: string) => (doc.seat_count = Number(value) || 0)
				"
			>
				<template #prefix>
					<span class="lucide-armchair size-4 text-ink-gray-5" />
				</template>
			</FormControl>
			<span class="ps-2 text-ink-gray-6">{{ seatsLabel }}</span>
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
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
	Combobox,
	createResource,
	DateRangePicker,
	FormControl,
	Select,
} from 'frappe-ui'
import { missingRing } from '@/components/InlineEdit/fieldClasses'
import TimeRangeField from '@/components/InlineEdit/TimeRangeField.vue'
import BatchSwitchFact from '@/pages/Batches/components/overview/BatchSwitchFact.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** The enrol card's facts as inline fields. */
const props = defineProps<{
	doc: LMSBatch
	form: BatchForm
	studentCount?: number
}>()

const ring = (key: string) => missingRing(props.form.isMissing(key))

const dates = computed<[string, string] | []>({
	get: () =>
		props.doc.start_date ? [props.doc.start_date, props.doc.end_date] : [],
	set: (range) => {
		props.doc.start_date = range[0] || ''
		props.doc.end_date = range[1] || ''
	},
})

const mediumOptions = computed(() => [
	{
		label: props.doc.zoom_account ? __('Online on Zoom') : __('Online'),
		value: 'Online',
	},
	{ label: __('In person'), value: 'Offline' },
])

const seatsLabel = computed<string>(() => {
	if (!props.doc.seat_count) return __('No seat limit')
	if (props.studentCount === undefined) return __('seats')
	const left = Math.max(props.doc.seat_count - props.studentCount, 0)
	return __('seats · {0} left').format(left)
})

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
