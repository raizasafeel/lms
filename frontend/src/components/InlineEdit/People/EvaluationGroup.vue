<template>
	<SettingsGroup
		:title="__('Evaluation and certificate')"
		icon="lucide-award"
		name="evaluation"
	>
		<SettingSwitch
			v-model="enabled"
			:label="__('Evaluations')"
			:summary="summary"
		/>
		<template v-if="enabled">
			<SettingRow :label="__('Evaluators')" :summary="evaluatorsSummary">
				<template #control>
					<MultiLink
						v-model="graders"
						doctype="User"
						url="lms.lms.api.search_users_by_role"
						:placeholder="__('Search evaluators')"
						:searchParams="{ roles: JSON.stringify(['Batch Evaluator']) }"
						:transform="toOptions"
						:extraOptions="knownGraders"
						:allowSelectAll="true"
						variant="subtle"
						class="w-fit"
						:aria-label="__('Add evaluator')"
					>
						<template #prefix>
							<span class="lucide-plus size-4 text-ink-gray-6" />
						</template>
						<template #summary>
							<span class="text-ink-gray-8">{{ __('Add evaluator') }}</span>
						</template>
						<template #item-prefix="{ item }">
							<Avatar :image="item.image" :label="item.label" size="sm" />
						</template>
						<template #item-label="{ item }">
							<PersonOption :label="item.label" :email="String(item.value)" />
						</template>
					</MultiLink>
				</template>
				<ul
					v-if="graders.length"
					class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 px-3"
					:aria-label="__('Evaluators')"
				>
					<PersonRow
						v-for="grader in graders"
						:key="grader"
						:name="describe(grader).full_name || grader"
						:image="describe(grader).user_image"
						:description="slotsLabel(grader)"
					>
						<template #actions>
							<Button
								variant="ghost"
								size="sm"
								:aria-label="
									__('Remove {0}').format(describe(grader).full_name || grader)
								"
								@click="graders = graders.filter((other) => other !== grader)"
							>
								<template #icon>
									<span class="lucide-x size-4" aria-hidden="true" />
								</template>
							</Button>
						</template>
					</PersonRow>
				</ul>
			</SettingRow>
			<SettingField
				v-model="format"
				type="select"
				:label="__('Format')"
				:summary="formatSummary"
				:options="formatOptions"
			/>
			<SettingField
				v-model="duration"
				type="select"
				:label="__('Length')"
				:summary="__('How long each evaluation takes.')"
				:options="durationOptions"
			/>
			<slot />
		</template>
		<slot name="certificate" />
	</SettingsGroup>
</template>

<script setup lang="ts">
import { Avatar, Button, createResource } from 'frappe-ui'
import { computed, watch } from 'vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import SettingField from '@/components/InlineEdit/SettingField.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import SettingSwitch from '@/components/InlineEdit/SettingSwitch.vue'
import PersonOption from '@/components/InlineEdit/People/PersonOption.vue'
import PersonRow from '@/components/InlineEdit/People/PersonRow.vue'
import {
	membersWith,
	withMembers,
	type PeopleDoctype,
	type PersonRow as Person,
} from '@/components/InlineEdit/People/people'
import { usePeopleDetails } from '@/components/InlineEdit/People/usePeopleDetails'
import type { Resource } from '@/types'

type Format = 'Live call' | 'Review of submitted work'

const REVIEW: Format = 'Review of submitted work'

/**
 * Who evaluates and how. The evaluators are the Grader rows of People, so
 * adding one here adds a Grader there and removing a Grader drops them here.
 */
const props = defineProps<{ doctype: PeopleDoctype }>()
const people = defineModel<Person[]>('people', { required: true })
const enabled = defineModel<boolean>('enabled', { required: true })
const format = defineModel<Format | undefined>('format')
const duration = defineModel<string | undefined>('duration')

const graders = computed<string[]>({
	get: () => membersWith(people.value, 'Grader'),
	set: (next) => {
		people.value = withMembers(props.doctype, people.value, 'Grader', next)
	},
})

const { describe, remember } = usePeopleDetails(() => graders.value)

const knownGraders = computed(() =>
	graders.value.map((grader) => ({
		label: describe(grader).full_name || grader,
		value: grader,
		image: describe(grader).user_image || '',
	}))
)

function toOptions(rows: Record<string, unknown>[]) {
	const hits = rows as {
		label?: string
		value?: string
		user_image?: string
		roles?: string[]
	}[]
	remember(
		hits.map((hit) => ({
			name: hit.value || '',
			full_name: hit.label,
			user_image: hit.user_image,
			roles: hit.roles || [],
		}))
	)
	return hits.map((hit) => ({
		label: hit.label || hit.value || '',
		value: hit.value || '',
		image: hit.user_image || '',
	}))
}

const openSlots = createResource({
	url: 'lms.lms.doctype.course_evaluator.course_evaluator.get_open_slot_counts',
	makeParams: () => ({ evaluators: JSON.stringify(graders.value) }),
}) as Resource<Record<string, number> | null>

watch(
	() => graders.value.join(','),
	(ids) => ids && openSlots.reload(),
	{ immediate: true }
)

function slotsLabel(grader: string): string {
	const count = openSlots.data?.[grader]
	if (count === undefined) return __('No schedule yet')
	return count === 1
		? __('1 open slot this week')
		: __('{0} open slots this week').format(count)
}

const formatOptions = [
	{ label: __('Live call'), value: 'Live call' },
	{ label: __('Review of submitted work'), value: REVIEW },
]
const durationOptions = ['15', '30', '45', '60'].map((minutes) => ({
	label: __('{0} minutes').format(minutes),
	value: minutes,
}))

// The rows below the switch show who and how, so the summary says only what learners do.
const summary = computed<string>(() =>
	enabled.value
		? __('Learners book a slot with whoever is free.')
		: __('Learners get no evaluation.')
)

const evaluatorsSummary = computed<string>(() => {
	const count = graders.value.length
	if (!count) return __('Add an evaluator so learners can book a slot.')
	return count === 1
		? __('1 evaluator, also listed as a Grader in People')
		: __('{0} evaluators, also listed as Graders in People').format(count)
})

const formatSummary = computed<string>(() =>
	format.value === REVIEW
		? __(
				'Reviews of submitted work are coming later. Until then learners book a live call.'
		  )
		: __('Learners meet their evaluator on a call.')
)
</script>
