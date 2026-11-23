<template>
	<div class="flex min-h-full flex-col">
		<div
			class="header-frame sticky top-0 z-20 justify-between gap-3 border-b bg-surface-base"
		>
			<div class="flex min-w-0 items-center gap-2 text-p-sm text-ink-gray-7">
				<span class="lucide-eye size-4 shrink-0" />
				<span class="text-p-sm-medium text-ink-gray-9">
					{{ __('Student view') }}
				</span>
				<span class="hidden truncate sm:inline">
					{{ __('· Nothing you do here is saved to a real learner') }}
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				<TabButtons v-model="mode" :options="modes" />
				<Button variant="outline" @click="emit('exit')">
					<template #prefix>
						<span class="lucide-x size-4" />
					</template>
					{{ __('Exit') }}
				</Button>
			</div>
		</div>
		<CourseOverview :course="course" :preview="mode" @enroll="enroll" />
	</div>
</template>

<script setup lang="ts">
import { Button, TabButtons, toast } from 'frappe-ui'
import CourseOverview from '@/pages/Courses/CourseOverview.vue'
import type { CourseDetails, Resource } from '@/types'

type PreviewMode = 'not-enrolled' | 'enrolled'

/** The course page as a learner sees it, before and after enrolling. */
defineProps<{ course: Resource<CourseDetails | null> }>()
const emit = defineEmits<{ exit: [] }>()

const mode = defineModel<PreviewMode>({ default: 'not-enrolled' })

const modes = [
	{
		label: __('Not enrolled'),
		value: 'not-enrolled',
		icon: 'lucide-user-round',
	},
	{ label: __('Enrolled'), value: 'enrolled', icon: 'lucide-user-round-check' },
]

function enroll(): void {
	mode.value = 'enrolled'
	toast.success(__('Switched to the enrolled view'))
}
</script>
