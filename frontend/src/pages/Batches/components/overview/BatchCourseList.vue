<template>
	<section v-if="editable || courses.data?.length">
		<div class="mb-4 flex items-baseline justify-between gap-4">
			<h2 class="text-3xl-semibold text-ink-gray-9">{{ __('Courses') }}</h2>
			<span v-if="courses.data?.length" class="text-p-base text-ink-gray-6">
				{{ courseCount }}
			</span>
		</div>
		<OverviewEmptyTile
			v-if="!courses.data?.length"
			icon="lucide-book-open"
			:title="__('No courses yet')"
			:description="__('Learners see the courses you add here, in this order.')"
		>
			<Button variant="subtle" @click="openPicker">
				<template #prefix>
					<span class="lucide-plus size-4" />
				</template>
				{{ __('Add course') }}
			</Button>
		</OverviewEmptyTile>
		<div v-else class="rounded-5 border border-outline-gray-2 p-2">
			<router-link
				v-for="course in courses.data"
				:key="course.name"
				:to="{ name: 'CourseDetail', params: { courseName: course.name } }"
				class="group/row flex items-center gap-3 rounded-3 px-2 py-2 hover:bg-surface-gray-1"
			>
				<div
					class="grid size-10 shrink-0 place-items-center overflow-hidden rounded-3"
					:class="
						course.image
							? 'bg-surface-gray-2'
							: courseTint(course.card_gradient)
					"
				>
					<img
						v-if="course.image"
						:src="safeUrl(course.image)"
						alt=""
						class="size-full object-cover"
					/>
					<span
						v-else
						:class="[courseIcon(course.icon), 'size-4']"
						aria-hidden="true"
					/>
				</div>
				<div class="min-w-0 flex-1">
					<div class="truncate text-p-base-medium text-ink-gray-9">
						{{ course.title }}
					</div>
					<div class="text-p-sm text-ink-gray-6">
						{{ __('{0} lessons').format(course.lessons || 0) }}
					</div>
				</div>
				<template v-if="course.membership && !hideProgress">
					<ProgressBar
						:progress="Math.round(course.membership.progress || 0)"
						class="!w-24"
					/>
					<span class="w-9 text-end text-p-sm tabular-nums text-ink-gray-6">
						{{ Math.round(course.membership.progress || 0) }}%
					</span>
				</template>
				<Button
					v-if="editable"
					variant="ghost"
					size="sm"
					:label="__('Remove {0}').format(course.title)"
					class="opacity-0 focus:opacity-100 group-hover/row:opacity-100"
					@click.prevent="removeCourse(course)"
				>
					<template #icon>
						<span class="lucide-x size-4" />
					</template>
				</Button>
			</router-link>
			<div v-if="editable" class="px-1 pt-1">
				<Button variant="ghost" @click="openPicker">
					<template #prefix>
						<span class="lucide-plus size-4" />
					</template>
					{{ __('Add course') }}
				</Button>
			</div>
		</div>
		<PickerDialog
			v-if="editable"
			v-model:open="pickerOpen"
			:title="__('Add courses')"
			:items="picker.items.value"
			:categories="picker.categories.value"
			@add="addCourses"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { Button, call, createResource, toast } from 'frappe-ui'
import { useOnboarding } from '@framework/ui/components/Onboarding/index'
import { useCoursePickerItems } from '@/composables/useCoursePickerItems'
import PickerDialog from '@/components/InlineEdit/PickerDialog.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import OverviewEmptyTile from '@/pages/Batches/components/overview/OverviewEmptyTile.vue'
import { seesOnboarding } from '@/utils/onboarding'
import { courseIcon } from '@/utils/courseIcons'
import { courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

interface BatchCourseCard {
	name: string
	title: string
	image?: string
	card_gradient?: string
	lessons?: number
	batch_course: string
	membership?: { progress?: number } | null
}

/** The batch's courses; editors add and remove them in place. */
const props = defineProps<{
	batchName?: string
	editable?: boolean
	/** A not-enrolled student view hides the instructor's own progress. */
	hideProgress?: boolean
	/** The batch's category; courses in it are suggested first. */
	category?: string | null
}>()

const pickerOpen = ref<boolean>(false)
const user = inject<{ data?: Parameters<typeof seesOnboarding>[0] }>('$user')
const { updateOnboardingStep } = useOnboarding('learning')

const courses = createResource({
	url: 'lms.lms.utils.get_batch_courses',
	makeParams: () => ({ batch: props.batchName }),
})

watch(
	() => props.batchName,
	(name) => {
		if (!name) return
		// A slow response for the previous batch would overwrite this one.
		courses.abort()
		courses.reload()
	},
	{ immediate: true }
)

const courseCount = computed(() => {
	const count = courses.data?.length ?? 0
	return count === 1 ? __('1 course') : __('{0} courses').format(count)
})

const selectedCourses = computed<string[]>(() =>
	(courses.data || []).map((course: BatchCourseCard) => course.name)
)

const errorMessage = (error: { messages?: string[] }, fallback: string) =>
	error.messages?.[0] || fallback

function insertCourse(course: string) {
	return call('frappe.client.insert', {
		doc: {
			doctype: 'Batch Course',
			course,
			parent: props.batchName,
			parenttype: 'LMS Batch',
			parentfield: 'courses',
		},
	})
}

async function addCourses(names: string[]): Promise<void> {
	// One at a time: each insert appends a row to the same batch.
	try {
		for (const name of names) await insertCourse(name)
		if (seesOnboarding(user?.data)) updateOnboardingStep('add_batch_course')
	} catch (error) {
		toast.error(
			errorMessage(
				error as { messages?: string[] },
				__('Could not add the course')
			)
		)
	}
	pickerOpen.value = false
	courses.reload()
}

const picker = useCoursePickerItems(
	() => selectedCourses.value,
	() => props.category
)

function openPicker(): void {
	pickerOpen.value = true
	picker.load()
}

function removeCourse(course: BatchCourseCard): void {
	call('frappe.client.delete', {
		doctype: 'Batch Course',
		name: course.batch_course,
	})
		.then(() => {
			toast.success(__('Course removed from batch'))
			courses.reload()
		})
		.catch((error: { messages?: string[] }) => {
			toast.error(errorMessage(error, __('Could not remove the course')))
		})
}
</script>
