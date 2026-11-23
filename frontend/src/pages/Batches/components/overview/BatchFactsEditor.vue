<template>
	<div class="space-y-2.5 text-p-base text-ink-gray-8">
		<div class="flex items-center gap-2.5 rounded-4" :class="ring('dates')">
			<span class="lucide-calendar size-4 shrink-0 text-ink-gray-5" />
			<DateRangePicker
				v-model="dates"
				variant="ghost"
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
				variant="ghost"
				format="h:mm a"
				:interval="30"
				:placeholder="__('Start')"
				:aria-label="__('Class start time')"
				class="w-28"
			/>
			<span class="text-ink-gray-6">–</span>
			<TimePicker
				v-model="doc.end_time"
				variant="ghost"
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
				variant="ghost"
				class="flex-1"
			/>
		</div>
		<div class="flex items-center gap-2.5">
			<span
				class="size-4 shrink-0 text-ink-gray-5"
				:class="doc.medium === 'Offline' ? 'lucide-map-pin' : 'lucide-video'"
			/>
			<Dropdown :options="mediumOptions">
				<Button variant="ghost">
					{{ doc.medium === 'Offline' ? __('In person') : __('Online') }}
					<template #suffix>
						<span class="lucide-chevron-down size-3.5 text-ink-gray-5" />
					</template>
				</Button>
			</Dropdown>
		</div>
		<div class="flex items-center gap-2.5">
			<span class="lucide-armchair size-4 shrink-0 text-ink-gray-5" />
			<FormControl
				:modelValue="doc.seat_count || ''"
				type="number"
				min="1"
				variant="subtle"
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
				variant="ghost"
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
	Button,
	Combobox,
	createResource,
	DatePicker,
	DateRangePicker,
	Dropdown,
	FormControl,
	TimePicker,
} from 'frappe-ui'
import BatchSwitchFact from '@/pages/Batches/components/overview/BatchSwitchFact.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** The enrol card's facts as inline fields. */
const props = defineProps<{ doc: LMSBatch; form: BatchForm }>()

const ring = (key: string) =>
	props.form.isMissing(key) && 'bg-surface-red-1 ring-2 ring-outline-red-3'

const dates = computed<[string, string] | []>({
	get: () =>
		props.doc.start_date ? [props.doc.start_date, props.doc.end_date] : [],
	set: (range) => {
		props.doc.start_date = range[0] || ''
		props.doc.end_date = range[1] || ''
	},
})

const mediumOptions = [
	{
		label: __('Online'),
		icon: 'lucide-video',
		onClick: () => (props.doc.medium = 'Online'),
	},
	{
		label: __('In person'),
		icon: 'lucide-map-pin',
		onClick: () => (props.doc.medium = 'Offline'),
	},
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
