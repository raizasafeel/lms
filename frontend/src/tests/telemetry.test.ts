/**
 * Tests for src/telemetry.js: the one wrapper every browser-side product event
 * goes through. What matters here is that it adds the standing context, that it
 * counts a repeated screen once, and above all that it cannot throw -- it runs
 * inside success handlers that have real work after them.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { captureMock, userData } = vi.hoisted(() => ({
	captureMock: vi.fn(),
	userData: { value: null as Record<string, unknown> | null },
}))

vi.mock('frappe-ui/frappe', () => ({
	useTelemetry: () => ({ capture: captureMock }),
}))
vi.mock('@/stores/user', () => ({
	usersStore: () => ({ userResource: { data: userData.value } }),
}))

import {
	captureEvent,
	captureEventOnce,
	resetCapturedEvents,
} from '@/telemetry'

beforeEach(() => {
	captureMock.mockReset()
	captureMock.mockImplementation(() => {})
	userData.value = null
	resetCapturedEvents()
	window.innerWidth = 1280
})

describe('captureEvent', () => {
	it('sends the event with the caller properties', () => {
		captureEvent('payment_gateway_created', { provider: 'Razorpay' })

		expect(captureMock).toHaveBeenCalledTimes(1)
		const [event, properties] = captureMock.mock.calls[0]
		expect(event).toBe('payment_gateway_created')
		expect(properties.provider).toBe('Razorpay')
	})

	it('adds the role and the surface to every event', () => {
		userData.value = { is_moderator: true }

		captureEvent('settings_page_opened', { page: 'raven' })

		const [, properties] = captureMock.mock.calls[0]
		expect(properties).toMatchObject({
			page: 'raven',
			role: 'moderator',
			surface: 'desktop',
		})
	})

	it.each([
		[{ is_moderator: true, is_instructor: true }, 'moderator'],
		[{ is_instructor: true }, 'course_creator'],
		[{ is_evaluator: true }, 'batch_evaluator'],
		[{ is_student: true }, 'student'],
	])('reports %o as %s', (user, expected) => {
		userData.value = user

		captureEvent('lesson_opened')

		expect(captureMock.mock.calls[0][1].role).toBe(expected)
	})

	it('reports an unresolved user rather than guessing a role', () => {
		captureEvent('lesson_opened')

		expect(captureMock.mock.calls[0][1].role).toBe('unknown')
	})

	it('reports a narrow viewport as mobile', () => {
		window.innerWidth = 480

		captureEvent('lesson_opened')

		expect(captureMock.mock.calls[0][1].surface).toBe('mobile')
	})

	it('lets the caller override the standing context', () => {
		userData.value = { is_moderator: true }

		captureEvent('lesson_opened', { role: 'student' })

		expect(captureMock.mock.calls[0][1].role).toBe('student')
	})

	it('swallows a telemetry failure instead of breaking the caller', () => {
		captureMock.mockImplementation(() => {
			throw new Error('pulse is down')
		})

		expect(() => captureEvent('lesson_opened')).not.toThrow()
	})
})

describe('captureEventOnce', () => {
	it('sends the event only once per page load', () => {
		captureEventOnce('course_editor_opened')
		captureEventOnce('course_editor_opened')

		expect(captureMock).toHaveBeenCalledTimes(1)
	})

	it('counts each dedupe key separately', () => {
		captureEventOnce('settings_page_opened', { page: 'raven' }, 'page:raven')
		captureEventOnce(
			'settings_page_opened',
			{ page: 'coupons' },
			'page:coupons',
		)
		captureEventOnce('settings_page_opened', { page: 'raven' }, 'page:raven')

		expect(captureMock).toHaveBeenCalledTimes(2)
		expect(captureMock.mock.calls.map(([, p]) => p.page)).toEqual([
			'raven',
			'coupons',
		])
	})

	it('does not block a later event after a failed send', () => {
		captureMock.mockImplementationOnce(() => {
			throw new Error('pulse is down')
		})

		captureEventOnce('a')
		captureEventOnce('b')

		expect(captureMock).toHaveBeenCalledTimes(2)
	})
})
