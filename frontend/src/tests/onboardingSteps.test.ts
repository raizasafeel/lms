/**
 * Tests for utils/onboardingSteps.ts: where each sidebar checklist step goes.
 *
 * The rule under test is that a step opens the form that finishes it, and that
 * a step needing a course or batch the site lacks falls back to the form that
 * creates one rather than going nowhere.
 */
import { describe, expect, it, vi } from 'vitest'

vi.mock('frappe-ui', () => ({ createResource: vi.fn() }))

import { destinationFor, STEPS_NEEDING_TARGETS } from '@/utils/onboardingSteps'

const NEW_COURSE = { type: 'form', to: { name: 'NewCourse' } }
const NEW_BATCH = { type: 'form', to: { name: 'NewBatch' } }

const newChapterOn = (courseName: string) => ({
	type: 'form',
	to: {
		name: 'ChapterForm',
		params: { courseName, chapterName: 'new' },
		hash: '#editor',
	},
})

describe('destinationFor', () => {
	it('opens the new course form', () => {
		expect(destinationFor('create_first_course')).toEqual(NEW_COURSE)
	})

	describe('first chapter', () => {
		it('opens the new chapter form on the admin course', () => {
			expect(
				destinationFor('create_first_chapter', { course: 'my-course' })
			).toEqual(newChapterOn('my-course'))
		})

		it('opens the new course form when there is no course yet', () => {
			expect(destinationFor('create_first_chapter', {})).toEqual(NEW_COURSE)
		})
	})

	describe('first lesson', () => {
		it('opens the course outline, where lessons are added', () => {
			expect(
				destinationFor('create_first_lesson', {
					course: 'my-course',
					course_has_chapter: true,
				})
			).toEqual({
				type: 'page',
				to: {
					name: 'CourseDetail',
					params: { courseName: 'my-course' },
					hash: '#editor',
				},
			})
		})

		it('asks for a chapter first when the course has none', () => {
			expect(
				destinationFor('create_first_lesson', {
					course: 'my-course',
					course_has_chapter: false,
				})
			).toEqual(newChapterOn('my-course'))
		})

		it('opens the new course form when there is no course yet', () => {
			expect(destinationFor('create_first_lesson', {})).toEqual(NEW_COURSE)
		})
	})

	it('opens the new quiz page', () => {
		expect(destinationFor('create_first_quiz')).toEqual({
			type: 'page',
			to: { name: 'NewQuiz' },
		})
	})

	it('opens the invite form in Settings > Members', () => {
		expect(destinationFor('invite_students')).toEqual({
			type: 'settings',
			slug: 'members',
			record: 'new',
		})
	})

	it('opens the new batch form', () => {
		expect(destinationFor('create_first_batch')).toEqual(NEW_BATCH)
	})

	it.each([
		['add_batch_student', 'NewBatchStudent'],
		['add_batch_course', 'NewBatchCourse'],
	])('%s opens %s on the admin batch', (step, form) => {
		expect(destinationFor(step, { batch: 'my-batch' })).toEqual({
			type: 'form',
			to: { name: form, params: { batchName: 'my-batch' }, hash: '' },
		})
	})

	it.each(['add_batch_student', 'add_batch_course'])(
		'%s opens the new batch form when there is no batch yet',
		(step) => {
			expect(destinationFor(step, {})).toEqual(NEW_BATCH)
		}
	)

	it('has nothing for a step it does not know', () => {
		expect(destinationFor('not_a_step')).toBeNull()
	})

	it('never sends a step to a list page', () => {
		const lists = new Set(['Courses', 'Batches', 'Quizzes'])
		const steps = [
			'create_first_course',
			'create_first_chapter',
			'create_first_lesson',
			'create_first_quiz',
			'invite_students',
			'create_first_batch',
			'add_batch_student',
			'add_batch_course',
		]
		for (const targets of [
			{},
			{ course: 'c', course_has_chapter: true, batch: 'b' },
		]) {
			for (const step of steps) {
				const destination = destinationFor(step, targets) as any
				expect(lists.has(destination?.to?.name)).toBe(false)
			}
		}
	})

	it('fetches targets only for the steps that depend on them', () => {
		expect([...STEPS_NEEDING_TARGETS].sort()).toEqual([
			'add_batch_course',
			'add_batch_student',
			'create_first_chapter',
			'create_first_lesson',
		])
	})
})
