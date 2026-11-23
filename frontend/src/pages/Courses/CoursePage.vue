<template>
	<CourseStudentView
		v-if="studentView"
		v-model="studentView"
		:course="course"
		@exit="studentView = null"
	/>
	<TabbedDetailPage
		v-else
		:tabs="tabs"
		:breadcrumbs="breadcrumbs"
		:published="Boolean(course.data?.published)"
		:loading="!course.data"
		:doc="course"
		doc-prop="course"
	>
		<template #status>
			<template v-if="isAdmin">
				<Badge :theme="course.data?.published ? 'green' : 'amber'">
					{{ course.data?.published ? __('Published') : __('Draft') }}
				</Badge>
				<Badge v-if="form.isDirty.value" theme="amber">
					{{ __('Not saved') }}
				</Badge>
			</template>
			<Badge v-else-if="course.data?.published" theme="green">
				{{ __('Published') }}
			</Badge>
		</template>
		<template #actions="{ tab }">
			<template v-if="isFormTab(tab?.key)">
				<CourseHeaderActions
					:course="course"
					:actions="actions"
					:canPublish="Boolean(user.data?.is_moderator)"
					@studentView="studentView = 'not-enrolled'"
				/>
				<CourseSaveButton v-if="isMobile" :form="form" />
			</template>
			<template v-if="tab?.key === 'editor' && editorSelected">
				<Tooltip
					v-if="courseEditorRef?.lessonHasVideo"
					:text="__('Video Statistics')"
				>
					<Button
						variant="ghost"
						:label="__('Video Statistics')"
						:class="isMobile ? '!size-9' : ''"
						@click="courseEditorRef?.openVideoStats()"
					>
						<template #icon>
							<span class="lucide-trending-up size-4" />
						</template>
					</Button>
				</Tooltip>
				<Tooltip v-if="!isMobile" :text="__('How to edit a lesson')">
					<Button
						variant="ghost"
						class="text-p-base-medium"
						:label="__('How to edit a lesson')"
						@click="showLessonHelp = true"
					>
						<template #icon>
							<span class="lucide-info size-4" />
						</template>
					</Button>
				</Tooltip>
				<Tooltip v-if="studentViewRoute && isMobile" :text="__('Student View')">
					<Button
						variant="outline"
						class="!size-9"
						:label="__('Student View')"
						:route="studentViewRoute"
					>
						<template #icon>
							<span class="lucide-eye size-4" />
						</template>
					</Button>
				</Tooltip>
				<Button
					v-else-if="studentViewRoute"
					variant="outline"
					:route="studentViewRoute"
				>
					<template #prefix>
						<span class="lucide-eye size-4" />
					</template>
					{{ __('Student View') }}
				</Button>
			</template>
			<Button
				v-if="tab?.key === 'dashboard' && course.data && isMobile"
				variant="outline"
				class="!size-9"
				:label="__('Enroll')"
				:tooltip="__('Enroll')"
				@click="openEnrollForm()"
			>
				<template #icon>
					<span class="lucide-plus size-4" />
				</template>
			</Button>
			<Button
				v-else-if="tab?.key === 'dashboard' && course.data"
				variant="outline"
				@click="openEnrollForm()"
			>
				<template #prefix>
					<span class="lucide-plus size-4" />
				</template>
				{{ __('Enroll') }}
			</Button>
		</template>

		<template #solo>
			<CourseOverview v-if="course.data" :course="course" />
			<SkeletonLoader v-else variant="course-page" />
		</template>

		<template #tab-body-editor>
			<div
				v-if="isMobile && editorSelected"
				class="flex items-center gap-2 border-b bg-surface-base px-5 py-2.5"
			>
				<Button
					variant="subtle"
					class="!size-9"
					:label="__('Previous lesson')"
					:disabled="!courseEditorRef?.hasPrev"
					@click="courseEditorRef?.goPrev()"
				>
					<template #icon>
						<span class="lucide-chevron-left size-4" />
					</template>
				</Button>
				<div
					class="min-w-0 flex-1 text-center text-p-xs font-medium tabular-nums text-ink-gray-6"
				>
					<span v-if="courseEditorRef?.lessonTotal">
						{{ courseEditorRef?.lessonIndex }} /
						{{ courseEditorRef?.lessonTotal }}
					</span>
				</div>
				<Button
					variant="subtle"
					class="!size-9"
					:label="__('Next lesson')"
					:disabled="!courseEditorRef?.hasNext"
					@click="courseEditorRef?.goNext()"
				>
					<template #icon>
						<span class="lucide-chevron-right size-4" />
					</template>
				</Button>
			</div>
			<CourseEditor
				ref="courseEditorRef"
				:course="course"
				v-model:selected="editorSelected"
			/>
		</template>

		<template #overlay="{ tab }">
			<div
				v-if="isFormTab(tab?.key) && !isMobile"
				class="pointer-events-none absolute end-0 top-0 z-10 flex h-12 items-center px-5"
			>
				<div class="pointer-events-auto">
					<CourseSaveButton :form="form" />
				</div>
			</div>
			<Button
				v-if="
					isMobile && tab?.key === 'editor' && courseEditorRef?.outlineVisible
				"
				variant="outline"
				size="md"
				class="absolute bottom-4 end-4 z-10 !h-11 !rounded-full !px-4 !shadow-lg"
				@click="courseEditorRef?.openChapters()"
			>
				<template #prefix>
					<span class="lucide-layers size-4" />
				</template>
				{{ __('Chapters') }}
			</Button>

			<div
				v-if="
					tab?.key === 'editor' &&
					course.data &&
					courseEditorRef?.outlineVisible
				"
				class="pointer-events-none absolute inset-x-0 top-0 z-10 hidden md:flex"
			>
				<div class="w-[70%]" />
				<!-- h-12 is the tab strip's height: the bar sits level with it, so
				     the two bottom borders have to meet. -->
				<div
					class="pointer-events-auto flex h-12 w-[30%] items-center justify-between gap-x-2 border-s border-b bg-surface-base px-5"
				>
					<div class="text-p-base-medium text-ink-gray-9">
						{{ __('Chapters') }}
					</div>
					<Button size="sm" @click="courseEditorRef?.openAddChapter()">
						<template #prefix>
							<span class="lucide-plus size-4" />
						</template>
						{{ __('Add') }}
					</Button>
				</div>
			</div>
		</template>
	</TabbedDetailPage>
	<LessonHelp v-model="showLessonHelp" />
</template>
<script setup lang="ts">
import { computed, inject, markRaw, provide, ref, watch } from 'vue'
import type { ComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Router } from 'vue-router'
import { Badge, Button, createResource, Tooltip, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { useScreenSize } from '@/utils/composables'
import TabbedDetailPage from '@/components/Layouts/pages/TabbedDetailPage.vue'
import type { DetailTab } from '@/components/Layouts/pages/TabbedDetailPage.vue'
import CourseOverview from '@/pages/Courses/CourseOverview.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import CourseDashboard from '@/pages/Courses/CourseDashboard.vue'
import CourseEditor from '@/pages/Courses/CourseEditor.vue'
import CourseForm from '@/pages/Courses/CourseForm.vue'
import LessonHelp from '@/components/LessonHelp.vue'
import CourseHeaderActions from '@/components/Courses/CourseHeaderActions.vue'
import CourseSaveButton from '@/components/Courses/CourseSaveButton.vue'
import CourseStudentView from '@/components/Courses/CourseStudentView.vue'
import { openFormRoute } from '@/composables/useFormRoute'
import { useCourseForm } from '@/composables/useCourseForm'
import {
	COURSE_ACTIONS,
	useCourseActions,
} from '@/composables/useCourseActions'
import {
	saveShortcut,
	useKeyboardShortcuts,
} from '@/composables/useKeyboardShortcuts'
import type { CourseDetails, Resource, SessionUser } from '@/types'
import { isInstructorOf } from '@/utils/instructors'

type Brand = { name?: string; logo?: string; favicon?: string }

const { brand } = sessionStore() as { brand: Brand }
const router: Router = useRouter()
const route = useRoute()
const user = inject<SessionUser>('$user')!
const { isMobile } = useScreenSize()

interface EditorSelection {
	chapterNumber: string
	lessonNumber: string
	number: string
	title?: string
}

const editorSelected = ref<EditorSelection | null>(null)
const showLessonHelp = ref(false)

// A lesson just created has no position until the outline reload places it.
const studentViewRoute = computed(() =>
	editorSelected.value?.number
		? {
				name: 'Lesson',
				params: {
					courseName: props.courseName,
					chapterNumber: editorSelected.value.chapterNumber,
					lessonNumber: editorSelected.value.lessonNumber,
				},
				query: { studentView: 1 },
		  }
		: null
)

type CourseEditorApi = {
	saveSelectedLesson: () => void
	isDirty: ComputedRef<boolean>
	lessonHasVideo: ComputedRef<boolean>
	openVideoStats: () => void
	openAddChapter: () => void
	outlineVisible: ComputedRef<boolean>
	lessonIndex: ComputedRef<number>
	lessonTotal: ComputedRef<number>
	hasPrev: ComputedRef<boolean>
	hasNext: ComputedRef<boolean>
	goPrev: () => void
	goNext: () => void
	openChapters: () => void
}
const courseEditorRef = ref<CourseEditorApi | null>(null)

// The enrollment form is a child route now, not a modal the dashboard tab owned,
// so the button navigates instead of reaching into the tab instance. Hash and
// query both travel: the hash names the tab this page returns to, and the query
// holds CourseEditor's open lesson.
function openEnrollForm() {
	openFormRoute(router, {
		name: 'NewCourseEnrollment',
		params: { courseName: props.courseName },
		hash: route.hash,
		query: { ...route.query },
	})
}

const props = defineProps<{
	courseName: string
}>()

// No `cache` key: one course's data would show while the next one loads.
const course = createResource({
	url: 'lms.lms.utils.get_course_details',
	makeParams() {
		return {
			course: props.courseName,
		}
	},
	auto: true,
}) as Resource<CourseDetails | null>

const tabs = computed<DetailTab[]>(() => [
	{
		key: 'overview',
		label: __('Overview'),
		component: markRaw(CourseOverview),
		icon: 'lucide-list',
		when: isAdmin.value,
		flow: true,
		rendersHeading: true,
	},
	{
		key: 'editor',
		label: __('Content'),
		component: markRaw(CourseEditor),
		icon: 'lucide-book-open',
		when: isAdmin.value,
	},
	{
		key: 'dashboard',
		label: __('Dashboard'),
		component: markRaw(CourseDashboard),
		icon: 'lucide-trending-up',
		when: isAdmin.value,
	},
	{
		key: 'settings',
		label: __('Options'),
		component: markRaw(CourseForm),
		icon: 'lucide-sliders-horizontal',
		when: isAdmin.value,
		flow: true,
	},
])

watch(course, () => {
	if (
		!isAdmin.value &&
		!course.data?.membership &&
		!course.data?.published &&
		!course.data?.upcoming
	) {
		router.push({
			name: 'Courses',
		})
	}
})

const isInstructor = (): boolean =>
	isInstructorOf(course.data?.instructors, user.data?.username)

const isAdmin = computed<boolean>(() => {
	return Boolean(user.data?.is_moderator) || isInstructor()
})

const form = useCourseForm(props.courseName, course, () => isAdmin.value)
const actions = useCourseActions(course)
provide(COURSE_ACTIONS, actions)

const studentView = ref<'not-enrolled' | 'enrolled' | null>(null)

const isFormTab = (key?: string): boolean =>
	isAdmin.value && (key === 'overview' || key === 'settings')

useKeyboardShortcuts({
	active: () =>
		!studentView.value && isFormTab(route.hash.slice(1) || 'overview'),
	ignoreTyping: false,
	shortcuts: [saveShortcut(() => form.submitCourse())],
})

const breadcrumbs = computed(() => {
	const crumbs: {
		label: string
		route: { name: string; params?: Record<string, string> }
	}[] = [{ label: __('Courses'), route: { name: 'Courses' } }]
	if (course.data) {
		crumbs.push({
			label: course.data.title,
			route: { name: 'CourseDetail', params: { courseName: course.data.name } },
		})
	}
	return crumbs
})

usePageMeta(() => {
	return {
		title: course.data?.title,
		icon: brand.favicon,
	}
})
</script>
