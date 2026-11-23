<template>
	<article
		class="relative isolate flex h-full flex-col gap-1.5 rounded-6 border border-outline-gray-2 bg-surface-base p-4 transition hover:border-outline-gray-3 hover:shadow-sm"
	>
		<h3 class="line-clamp-2 text-base-semibold leading-snug text-ink-gray-9">
			<CardLink :to="to">{{ batch.title }}</CardLink>
		</h3>
		<p v-if="batch.description" class="line-clamp-2 text-p-sm text-ink-gray-6">
			{{ batch.description }}
		</p>

		<!-- First visually, after the title in reading and tab order. -->
		<div class="order-first flex min-h-6 items-center justify-between gap-2">
			<span
				class="truncate text-p-xs-medium uppercase tracking-wide text-ink-gray-6"
			>
				{{ batch.category }}
			</span>
			<span class="flex -space-x-1.5">
				<template
					v-for="instructor in instructors"
					:key="instructor.username || instructor.full_name"
				>
					<router-link
						v-if="instructor.username"
						:to="{
							name: 'Profile',
							params: { username: instructor.username },
						}"
						:aria-label="instructor.full_name"
						:title="instructor.full_name"
						class="relative z-10 rounded-full"
					>
						<UserAvatar :user="instructor" size="sm" />
					</router-link>
					<UserAvatar v-else :user="instructor" size="sm" />
				</template>
			</span>
		</div>

		<ul class="mt-3 space-y-2 text-p-sm text-ink-gray-7">
			<li class="flex items-center gap-2">
				<span
					class="lucide-calendar size-4 text-ink-gray-5"
					aria-hidden="true"
				/>
				{{ getFormattedDateRange(batch.start_date, batch.end_date) }}
			</li>
			<li v-if="batch.start_time" class="flex items-center gap-2">
				<span class="lucide-clock size-4 text-ink-gray-5" aria-hidden="true" />
				<span dir="ltr">
					{{ formatTime(batch.start_time) }} – {{ formatTime(batch.end_time) }}
				</span>
			</li>
			<li v-if="batch.timezone" class="flex items-center gap-2">
				<span class="lucide-globe size-4 text-ink-gray-5" aria-hidden="true" />
				{{ timezone }}
			</li>
			<li v-if="batch.certification" class="flex items-center gap-2">
				<span
					class="lucide-circle-check size-4 text-ink-gray-5"
					aria-hidden="true"
				/>
				{{ __('Certificate') }}
			</li>
		</ul>

		<div class="mt-auto flex items-center gap-2 pt-4">
			<Badge v-if="status" :theme="status.theme" :label="status.label" />
			<span
				class="ms-auto shrink-0"
				:class="
					batch.paid_batch
						? 'text-sm-semibold text-ink-gray-9'
						: 'text-p-sm text-ink-gray-7'
				"
			>
				{{ batch.paid_batch ? batch.price : __('Free') }}
			</span>
		</div>
	</article>
</template>
<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import { formatTime, getFormattedDateRange } from '@/utils'
import { formatTimezone, nextOccurrence } from '@/utils/timezone'
import CardLink from '@/components/CardLink.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ProgressBar from '@/components/ProgressBar.vue'

const props = defineProps({
	batch: {
		type: Object,
		default: null,
	},
	to: {
		type: [Object, String],
		default: null,
	},
})

const instructors = computed(() => (props.batch.instructors || []).slice(0, 3))

const timezone = computed(() =>
	formatTimezone(
		props.batch.timezone,
		nextOccurrence(props.batch.start_date, props.batch.end_date)
	)
)

const status = computed(() => {
	const { is_enrolled, seat_count, seats_left } = props.batch
	if (is_enrolled) return { theme: 'green', label: __('Enrolled') }
	if (!seat_count) return null
	if (seats_left <= 0) return { theme: 'red', label: __('Sold out') }
	return {
		theme: 'amber',
		label:
			seats_left == 1
				? __('1 seat left')
				: __('{0} seats left').format(seats_left),
	}
})
</script>
