<template>
	<section v-if="classes.length || editable">
		<div class="mb-4 flex items-baseline justify-between gap-4">
			<h2 class="text-3xl-semibold text-ink-gray-9">{{ __('Schedule') }}</h2>
			<span v-if="classes.length" class="text-p-base text-ink-gray-6">
				{{ countLabel }}
			</span>
		</div>
		<p
			v-if="!classes.length"
			class="rounded-5 border border-outline-gray-2 px-4 py-3 text-p-base text-ink-gray-7"
		>
			{{
				__(
					'No classes yet. Learners see the schedule here once you add classes.'
				)
			}}
			<router-link
				v-if="batchName"
				:to="{ hash: '#classes' }"
				class="font-medium text-ink-gray-9 underline-offset-2 hover:underline"
			>
				{{ __('Add a class') }}
			</router-link>
		</p>
		<ul
			v-else
			class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
		>
			<li
				v-for="liveClass in nextClasses"
				:key="liveClass.name"
				class="flex items-center gap-4 px-4 py-2.5 text-p-base"
			>
				<span class="w-24 shrink-0 text-p-sm text-ink-gray-6">
					{{ dayjs(liveClass.date).format('ddd, D MMM') }}
				</span>
				<span class="min-w-0 flex-1 truncate text-ink-gray-8">
					{{ liveClass.title }}
				</span>
			</li>
			<li v-if="classes.length > nextClasses.length">
				<router-link
					:to="{ hash: '#classes' }"
					class="block px-4 py-2 text-p-sm text-ink-gray-6 hover:bg-surface-gray-1"
				>
					{{ __('Show all {0} classes').format(classes.length) }}
				</router-link>
			</li>
		</ul>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createListResource } from 'frappe-ui'
import dayjs from '@/utils/dayjs'

interface LiveClassRow {
	name: string
	title: string
	date: string
}

const SHOWN = 4

/** The batch's next live classes, with a link to the Classes tab. */
const props = defineProps<{
	/** Unset for a batch not saved yet, which has no classes. */
	batchName?: string
	/** Editors see the empty schedule; learners see nothing until classes exist. */
	editable?: boolean
}>()

const liveClasses = createListResource({
	doctype: 'LMS Live Class',
	filters: { batch_name: props.batchName },
	fields: ['name', 'title', 'date'],
	orderBy: 'date asc, time asc',
	pageLength: 500,
	auto: Boolean(props.batchName),
})

const classes = computed<LiveClassRow[]>(() => liveClasses.data || [])

// Upcoming first; once the batch is over, its last few.
const nextClasses = computed<LiveClassRow[]>(() => {
	const today = dayjs().format('YYYY-MM-DD')
	const upcoming = classes.value.filter((row) => row.date >= today)
	return upcoming.length
		? upcoming.slice(0, SHOWN)
		: classes.value.slice(-SHOWN)
})

const countLabel = computed<string>(() =>
	classes.value.length === 1
		? __('1 live class')
		: __('{0} live classes').format(classes.value.length)
)
</script>
