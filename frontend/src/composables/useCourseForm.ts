import { createDocumentResource, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import { computed, nextTick, provide, reactive, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { getMetaInfo, updateMetaInfo } from '@/utils'
import { joinLabels, missingCourseFields } from '@/utils/courseForm'
import type { MissingField } from '@/utils/courseForm'
import { reportAutosaveError, submitResource } from '@/utils/resource'
import {
	membersWith,
	withMembers,
	type PersonRow,
} from '@/components/InlineEdit/People/people'
import type { LMSCourse } from '@/types/lms/LMSCourse'
import type {
	CourseDetails,
	CourseFormContext,
	CourseFormMeta,
	Resource,
} from '@/types'

const CHECKBOXES: (keyof LMSCourse)[] = [
	'published',
	'upcoming',
	'disable_self_learning',
	'enforce_lesson_completion',
	'paid_course',
	'featured',
	'enable_certification',
	'paid_certificate',
]

export interface CourseForm extends CourseFormContext {
	isDirty: Ref<boolean>
	showRequired: Ref<boolean>
	missingFields: ComputedRef<MissingField[]>
	isMissing: (key: string) => boolean
	isSaving: () => boolean
	/** Resolves true once the course is saved or had nothing to save. */
	submitCourse: () => Promise<boolean>
}

/**
 * The course's editable state, shared by the Overview and Options tabs.
 * Loads only once `enabled` is true, so learners never fetch the raw doc.
 */
export function useCourseForm(
	courseName: string,
	course: Resource<CourseDetails | null>,
	enabled: () => boolean
): CourseForm {
	const resource = createDocumentResource({
		doctype: 'LMS Course',
		name: courseName,
		auto: false,
	}) as Resource<LMSCourse | null>

	const isDirty = ref<boolean>(false)
	const showRequired = ref<boolean>(false)
	const people = ref<PersonRow[]>([])
	// Editors are the instructors learners see; the role table is the one owner.
	const instructors = computed<string[]>({
		get: () => membersWith(people.value, 'Editor'),
		set: (editors) => {
			people.value = withMembers('LMS Course', people.value, 'Editor', editors)
		},
	})
	const relatedCourses = ref<string[]>([])
	const meta = reactive<CourseFormMeta>({ description: '', keywords: '' })
	// Set while server data is applied, so it does not arm autosave.
	let applyingServerData = false

	const missingFields = computed<MissingField[]>(() =>
		missingCourseFields({
			doc: resource.doc ?? null,
			instructors: instructors.value,
		})
	)

	const isMissing = (key: string): boolean =>
		showRequired.value && missingFields.value.some((f) => f.key === key)

	watch(missingFields, (missing) => {
		if (!missing.length) showRequired.value = false
	})

	watch(enabled, (on) => on && !resource.doc && resource.reload(), {
		immediate: true,
	})

	watch(
		() => resource.doc,
		(doc) => {
			if (!doc) return
			applyingServerData = true
			getMetaInfo('courses', doc.name, meta)
			applyServerData(doc)
			nextTick(() => {
				applyingServerData = false
			})
		}
	)

	function applyServerData(doc: LMSCourse): void {
		people.value = (doc.people || []).map(({ member, role }) => ({
			member,
			role,
		}))
		relatedCourses.value = (doc.related_courses || [])
			.map((row) => row.course)
			.filter(Boolean) as string[]
		for (const key of CHECKBOXES) {
			;(doc as Record<string, unknown>)[key] = Boolean(doc[key])
		}
	}

	function markDirty(): void {
		if (applyingServerData) return
		isDirty.value = true
	}

	const isSaving = (): boolean => Boolean(resource.setValue.loading)

	async function submitCourse(): Promise<boolean> {
		if (isSaving()) return false
		const missing = missingFields.value
		if (missing.length) {
			showRequired.value = true
			toast.error(
				__('Add {0} before saving.').format(
					joinLabels(missing.map((f) => f.label))
				)
			)
			return false
		}
		return isDirty.value ? updateCourse() : true
	}

	// Whole-doc last-write-wins: a stale `modified` would trip Frappe's
	// timestamp guard after a publish toggle or lesson autosave.
	async function updateCourse(): Promise<boolean> {
		const fields: Record<string, unknown> = { ...resource.doc }
		delete fields.modified
		let saved = false
		await submitResource(
			resource.setValue,
			{
				...fields,
				people: people.value,
				instructors: instructors.value.map((i) => ({ instructor: i })),
				related_courses: relatedCourses.value.map((c) => ({ course: c })),
			},
			{
				onSuccess() {
					saved = true
					updateMetaInfo('courses', resource.doc?.name, meta)
					toast.success(__('Course updated successfully'))
					isDirty.value = false
					resource.reload()
					course.reload()
				},
				onError(error: FrappeResourceError) {
					reportAutosaveError(error)
				},
			}
		)
		return saved
	}

	const form: CourseForm = {
		resource,
		people,
		instructors,
		relatedCourses,
		meta,
		markDirty,
		isDirty,
		showRequired,
		missingFields,
		isMissing,
		isSaving,
		submitCourse,
	}
	provide<CourseFormContext>('courseForm', form)
	return form
}
