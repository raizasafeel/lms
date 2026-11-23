<template>
	<SkeletonLoader v-if="!course.data" variant="course-page" />
	<div v-else class="p-5">
		<div
			class="flex flex-col md:flex-row items-start justify-between w-full gap-x-8 gap-y-8"
		>
			<div class="md:w-2/3 space-y-10 min-w-0">
				<CourseHeading :course="course.data" :editable="editable" />
				<div class="md:hidden">
					<CourseEditCard v-if="editable" :course="course" />
					<CourseCardOverlay
						v-else
						:course="course"
						:preview="preview"
						@enroll="emit('enroll')"
					/>
				</div>

				<section>
					<div class="flex items-baseline justify-between gap-4 mb-4">
						<h2 class="text-3xl-semibold text-ink-gray-9">
							{{ __('Course content') }}
						</h2>
						<div class="text-base text-ink-gray-6">
							{{ outlineStats }}
						</div>
					</div>
					<div class="border rounded-5 p-2">
						<SkeletonLoader
							v-if="outline.loading && !outline.data"
							variant="course-outline"
							:count="10"
						/>
						<div
							v-else-if="!hasCourseContent"
							class="flex items-center justify-center px-4 py-10 text-center"
						>
							<span class="text-sm text-ink-gray-6">
								{{ __('Course content coming soon!') }}
							</span>
						</div>
						<CourseOutline
							v-else
							:courseName="course.data.name"
							:getProgress="course.data.membership ? true : false"
							:editorLinks="isCourseAdmin && !preview"
						/>
					</div>
				</section>

				<section v-if="editable && form?.resource.doc" class="space-y-3">
					<h2 :id="aboutHeadingId" class="text-3xl-semibold text-ink-gray-9">
						{{ __('About this course') }}
					</h2>
					<div
						class="-mx-2.5 rounded-5 px-2.5 py-1.5 hover:bg-surface-gray-2 focus-within:hover:bg-transparent"
						:class="
							form.isMissing?.('description') &&
							'bg-surface-red-1 ring-2 ring-outline-red-3'
						"
					>
						<RichTextEditor
							:ariaLabelledby="aboutHeadingId"
							:content="form.resource.doc.description"
							variant="ghost"
							:placeholder="
								__(
									'Describe what the course covers, who it is for and what learners can do at the end.'
								)
							"
							minHeight="5rem"
							@change="setDescription"
						/>
					</div>
				</section>
				<section v-else-if="course.data.description" class="space-y-3">
					<h2 class="text-3xl-semibold text-ink-gray-9">
						{{ __('About this course') }}
					</h2>
					<div
						v-safe-html:rich="course.data.description"
						class="ProseMirror prose prose-sm max-w-none !whitespace-normal prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2"
					/>
				</section>

				<CourseReviews
					:courseName="course.data.name"
					:avg_rating="course.data.rating"
					:membership="course.data.membership || null"
				/>
			</div>

			<aside
				class="hidden md:flex w-80 shrink-0 flex-col space-y-6 self-start sticky top-5"
			>
				<CourseEditCard v-if="editable" :course="course" />
				<template v-else>
					<CourseCardOverlay
						:course="course"
						:preview="preview"
						@enroll="emit('enroll')"
					/>
					<CourseCreatorCard :instructors="course.data.instructors || []" />
				</template>
			</aside>
		</div>

		<section v-if="editable && form" class="mt-12 space-y-4">
			<div class="flex items-baseline justify-between gap-4">
				<h2 class="text-3xl-semibold text-ink-gray-9">
					{{ __('Related courses') }}
				</h2>
				<span class="text-p-sm text-ink-gray-6">
					{{ __('Shown to learners below the course') }}
				</span>
			</div>
			<MultiLink
				v-model="form.relatedCourses.value"
				doctype="LMS Course"
				:filters="{ name: ['!=', course.data.name], published: 1 }"
				:placeholder="__('Add related courses')"
				:emptyText="__('No other published courses available')"
				variant="outline"
				@update:modelValue="form.markDirty()"
			/>
		</section>
		<RelatedCourses v-else :courseName="course.data.name" class="mt-12" />
	</div>
</template>

<script setup lang="ts">
import { computed, inject, useId, watch } from 'vue'
import { createResource } from 'frappe-ui'
import type {
	CourseDetails,
	CourseFormContext,
	OutlineChapter,
	Resource,
	SessionUser,
} from '@/types'
import CourseCardOverlay from '@/components/CourseCardOverlay.vue'
import CourseOutline from '@/components/CourseOutline.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import CourseReviews from '@/components/CourseReviews.vue'
import CourseCreatorCard from '@/components/CourseCreatorCard.vue'
import RelatedCourses from '@/components/RelatedCourses.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import CourseEditCard from '@/components/Courses/CourseEditCard.vue'
import CourseHeading from '@/components/Courses/CourseHeading.vue'
import { isInstructorOf } from '@/utils/instructors'

/** The course page. Instructors edit it in place; learners and previews read it. */
const props = defineProps<{
	course: Resource<CourseDetails | null>
	preview?: 'not-enrolled' | 'enrolled' | null
}>()

const emit = defineEmits<{ enroll: [] }>()

const user = inject<SessionUser>('$user')
const form = inject<CourseFormContext | null>('courseForm', null)
const aboutHeadingId = useId()

const editable = computed<boolean>(
	() => !props.preview && Boolean(form?.resource.doc)
)

const isCourseAdmin = computed<boolean>(
	() =>
		Boolean(user?.data?.is_moderator) ||
		isInstructorOf(props.course.data?.instructors, user?.data?.username)
)

function setDescription(value: string): void {
	if (!form?.resource.doc) return
	form.resource.doc.description = value
	form.markDirty()
}

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	makeParams() {
		return { course: props.course.data?.name, progress: false }
	},
	auto: false,
}) as Resource<OutlineChapter[]>

watch(
	() => props.course.data?.name,
	(name) => {
		if (name) outline.fetch()
	},
	{ immediate: true }
)

const outlineStats = computed(() => {
	const chapters = outline.data || []
	const lessonCount = chapters.reduce(
		(acc, c) => acc + (c.lessons?.length || 0),
		0
	)
	const parts: string[] = []
	if (chapters.length) {
		parts.push(
			chapters.length === 1
				? __('1 section')
				: __('{0} sections').format(chapters.length)
		)
	}
	if (lessonCount) {
		parts.push(
			lessonCount === 1 ? __('1 lesson') : __('{0} lessons').format(lessonCount)
		)
	}
	return parts.join(' · ')
})

const hasCourseContent = computed(() => {
	const chapters = outline.data || []
	const lessonCount = chapters.reduce(
		(acc, c) => acc + (c.lessons?.length || 0),
		0
	)
	return chapters.length > 0 && lessonCount > 0
})
</script>
