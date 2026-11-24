<template>
	<div
		class="sticky top-0 z-20 flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-outline-gray-2 bg-surface-base px-5 py-2"
		role="region"
		:aria-label="__('Student view')"
	>
		<div class="flex min-w-0 items-center gap-2 text-p-sm text-ink-gray-7">
			<span class="lucide-eye size-4 shrink-0" />
			<span class="text-p-sm-medium text-ink-gray-9">
				{{ __('Student view') }}
			</span>
			<span class="hidden truncate sm:inline">
				· {{ __('Nothing you do here is saved to a real learner') }}
			</span>
		</div>
		<div class="flex shrink-0 items-center gap-2">
			<Button
				v-if="mode === 'enrolled'"
				variant="ghost"
				:loading="reset.loading"
				:aria-label="__('Reset progress')"
				class="max-sm:w-7 max-sm:px-0"
				@click="showReset = true"
			>
				<template #prefix>
					<span class="lucide-rotate-ccw size-4" />
				</template>
				<span class="hidden sm:inline">{{ __('Reset progress') }}</span>
			</Button>
			<TabButtons v-model="mode" :options="modes" />
			<Button variant="outline" :aria-label="__('Exit')" @click="emit('exit')">
				<template #prefix>
					<span class="lucide-x size-4" />
				</template>
				<span class="hidden sm:inline">{{ __('Exit') }}</span>
			</Button>
		</div>
	</div>
	<Dialog
		v-model:open="showReset"
		:title="__('Reset your progress?')"
		:message="resetMessage"
		:actions="[
			{
				label: __('Reset progress'),
				variant: 'solid',
				theme: 'red',
				onClick: resetProgress,
			},
		]"
	/>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, createResource, Dialog, TabButtons, toast } from 'frappe-ui'
import type { Resource } from '@/types'
import { resourceErrorMessage, submitResource } from '@/utils/resource'

type StudentMode = 'not-enrolled' | 'enrolled'

/**
 * Student view controls. Enrolled gives the instructor a real enrollment of
 * their own, so lessons, quizzes and progress behave as for a learner.
 */
const props = defineProps<{
	doctype: 'LMS Course' | 'LMS Batch'
	name: string
}>()
const emit = defineEmits<{ exit: []; change: [] }>()
const mode = defineModel<StudentMode>({ required: true })

const showReset = ref(false)

const modes = [
	{
		label: __('Not enrolled'),
		value: 'not-enrolled',
		iconLeft: 'lucide-user-round',
	},
	{
		label: __('Enrolled'),
		value: 'enrolled',
		iconLeft: 'lucide-user-round-check',
	},
]

const resetMessage = computed(() =>
	props.doctype === 'LMS Batch'
		? __(
				'This deletes your completed lessons, quiz and assignment submissions in every course of this batch. Learners are not affected. This cannot be undone.'
		  )
		: __(
				'This deletes your completed lessons, quiz and assignment submissions in this course. Learners are not affected. This cannot be undone.'
		  )
)

const params = () => ({ doctype: props.doctype, name: props.name })

const enroll = createResource({
	url: 'lms.lms.student_view.enroll_self',
	makeParams: params,
}) as Resource<null>

const reset = createResource({
	url: 'lms.lms.student_view.reset_own_progress',
	makeParams: params,
}) as Resource<null>

function failed(error: unknown): void {
	toast.error(resourceErrorMessage(error))
}

watch(
	mode,
	(value) => {
		if (value !== 'enrolled') return
		submitResource(
			enroll,
			{},
			{
				onSuccess: () => emit('change'),
				onError(error) {
					mode.value = 'not-enrolled'
					failed(error)
				},
			}
		)
	},
	{ immediate: true }
)

function resetProgress(): void {
	showReset.value = false
	submitResource(
		reset,
		{},
		{
			onSuccess() {
				toast.success(__('Your progress was reset'))
				emit('change')
			},
			onError: failed,
		}
	)
}
</script>
