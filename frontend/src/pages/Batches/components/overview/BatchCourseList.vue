<template>
	<section v-if="editable || courses.data?.length">
		<div class="mb-4 flex items-baseline justify-between gap-4">
			<h2 class="text-3xl-semibold text-ink-gray-9">{{ __('Courses') }}</h2>
			<span v-if="courses.data?.length" class="text-p-base text-ink-gray-6">
				{{ courseCount }}
			</span>
		</div>
		<div class="rounded-5 border border-outline-gray-2 p-2">
			<router-link
				v-for="course in courses.data"
				:key="course.name"
				:to="{ name: 'CourseDetail', params: { courseName: course.name } }"
				class="group/row flex items-center gap-3 rounded-3 px-2 py-2 hover:bg-surface-gray-1"
			>
				<div
					class="grid size-10 shrink-0 place-items-center overflow-hidden rounded-3 bg-surface-gray-2"
				>
					<img
						v-if="course.image"
						:src="safeUrl(course.image)"
						alt=""
						class="size-full object-cover"
					/>
					<span v-else class="lucide-book-open size-4 text-ink-gray-5" />
				</div>
				<div class="min-w-0 flex-1">
					<div class="truncate text-p-base-medium text-ink-gray-9">
						{{ course.title }}
					</div>
					<div class="text-p-sm text-ink-gray-6">
						{{ __('{0} lessons').format(course.lessons || 0) }}
					</div>
				</div>
				<template v-if="course.membership">
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
			<div
				v-if="!courses.data?.length"
				class="px-2 py-6 text-center text-p-base text-ink-gray-6"
			>
				{{ __('Add the courses learners take in this batch.') }}
			</div>
			<div v-if="editable" class="px-1 pt-1">
				<Button variant="ghost" @click="openCourseForm">
					<template #prefix>
						<span class="lucide-plus size-4" />
					</template>
					{{ __('Add course') }}
				</Button>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, call, createResource, toast } from 'frappe-ui'
import ProgressBar from '@/components/ProgressBar.vue'
import { openBatchForm } from '@/composables/useBatchForms'
import { safeUrl } from '@/utils/safeUrl'

interface BatchCourseCard {
	name: string
	title: string
	image?: string
	lessons?: number
	batch_course: string
	membership?: { progress?: number } | null
}

/** The batch's courses; editors add and remove them in place. */
const props = defineProps<{ batchName?: string; editable?: boolean }>()

const route = useRoute()
const router = useRouter()

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

// The add form is a child route; refresh once it closes.
watch(
	() => route.name,
	(current, previous) => {
		if (previous === 'NewBatchCourse' && current !== previous) courses.reload()
	}
)

const courseCount = computed(() => {
	const count = courses.data?.length ?? 0
	return count === 1 ? __('1 course') : __('{0} courses').format(count)
})

function openCourseForm(): void {
	openBatchForm(router, 'NewBatchCourse', props.batchName ?? '', route.hash)
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
			toast.error(error.messages?.[0] || __('Could not remove the course'))
		})
}
</script>
