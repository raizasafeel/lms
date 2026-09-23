/**
 * Where each onboarding checklist step takes the admin who clicks it.
 *
 * Every step opens the form that finishes it, not the list the form lives
 * behind: "Create your first batch" opens the new-batch form, "Invite your team"
 * opens the invite form in Settings > Members. A step that needs a course or a
 * batch the site does not have yet falls back to the form that creates one,
 * so no click is a dead end.
 *
 * Kept free of the router and the checklist so each step's destination can be
 * asserted on its own.
 */
import type { RouteLocationRaw } from 'vue-router'
import { batchRouteLocation } from '@/composables/useBatchForms'

/** What `lms.lms.onboarding.get_onboarding_targets` returns. */
export interface OnboardingTargets {
	course?: string | null
	course_has_chapter?: boolean
	batch?: string | null
}

export type OnboardingDestination =
	/** A routed modal form, opened over the current page. */
	| { type: 'form'; to: RouteLocationRaw }
	/** A full page. */
	| { type: 'page'; to: RouteLocationRaw }
	/** A Settings panel, optionally straight into one of its records. */
	| { type: 'settings'; slug: string; record?: string }

/** Steps whose destination depends on which course or batch the site has. */
export const STEPS_NEEDING_TARGETS = new Set([
	'create_first_chapter',
	'create_first_lesson',
	'add_batch_student',
	'add_batch_course',
])

// The course page tab that holds the outline, where chapters and lessons are
// added. Its Settings tab is the course's own fields and has neither.
const COURSE_OUTLINE_TAB = '#editor'

const NEW_COURSE: OnboardingDestination = {
	type: 'form',
	to: { name: 'NewCourse' },
}

const NEW_BATCH: OnboardingDestination = {
	type: 'form',
	to: { name: 'NewBatch' },
}

const newChapter = (courseName: string): OnboardingDestination => ({
	type: 'form',
	to: {
		name: 'ChapterForm',
		params: { courseName, chapterName: 'new' },
		hash: COURSE_OUTLINE_TAB,
	},
})

export function destinationFor(
	step: string,
	targets: OnboardingTargets = {}
): OnboardingDestination | null {
	const { course, course_has_chapter, batch } = targets

	switch (step) {
		case 'create_first_course':
			return NEW_COURSE

		case 'create_first_chapter':
			return course ? newChapter(course) : NEW_COURSE

		case 'create_first_lesson':
			// A lesson is added inline from the course outline, and it needs a
			// chapter to go in. No chapter yet means that step comes first.
			if (!course) return NEW_COURSE
			if (!course_has_chapter) return newChapter(course)
			return {
				type: 'page',
				to: {
					name: 'CourseDetail',
					params: { courseName: course },
					hash: COURSE_OUTLINE_TAB,
				},
			}

		case 'create_first_quiz':
			// The quiz form is a full page, not a modal.
			return { type: 'page', to: { name: 'NewQuiz' } }

		case 'invite_students':
			return { type: 'settings', slug: 'members', record: 'new' }

		case 'create_first_batch':
			return NEW_BATCH

		case 'add_batch_student':
			return batch
				? {
						type: 'form',
						to: batchRouteLocation('NewBatchStudent', batch, ''),
					}
				: NEW_BATCH

		case 'add_batch_course':
			return batch
				? {
						type: 'form',
						to: batchRouteLocation('NewBatchCourse', batch, ''),
					}
				: NEW_BATCH

		default:
			return null
	}
}
