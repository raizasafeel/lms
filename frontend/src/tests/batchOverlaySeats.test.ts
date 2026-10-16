import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
// @ts-expect-error a JS SFC has no generated types (TS7016)
import BatchOverlay from '@/pages/Batches/components/BatchOverlay.vue'

vi.mock('frappe-ui', () => ({
	createResource: () => ({ submit: vi.fn() }),
	toast: { success: vi.fn(), error: vi.fn() },
	Badge: {
		props: ['label'],
		template: `<span class="badge">{{ label }}</span>`,
	},
	Button: {
		inheritAttrs: false,
		props: ['route'],
		template: `<button v-bind="$attrs"><slot /></button>`,
	},
}))

vi.mock('@/utils', () => ({
	formatNumberIntoCurrency: (amount: number) => String(amount),
	formatTime: (time: string) => time,
	getFormattedDateRange: () => '',
}))

vi.mock('@/utils/timezone', () => ({
	formatTimezone: () => '',
	nextOccurrence: () => null,
}))

vi.mock('@/components/VideoPreview.vue', () => ({
	default: { render: () => null },
}))

function mountOverlay(data: Record<string, unknown>) {
	return mount(BatchOverlay, {
		props: {
			batch: {
				data: {
					name: 'B1',
					courses: [],
					start_date: '2099-01-01',
					end_date: '2099-01-10',
					start_time: '09:00:00',
					end_time: '11:00:00',
					accept_enrollments: 1,
					...data,
				},
			},
		},
		global: {
			provide: { $user: { data: { name: 'stu@example.com' } } },
			mocks: { __: (text: string) => text },
		},
	})
}

describe('BatchOverlay seat limits', () => {
	// Regression: no Register/Enroll on a batch without a seat limit (#3028,
	// fixed in #3035).
	it('offers to join a batch with no seat limit', () => {
		const paid = mountOverlay({ paid_batch: 1, seat_count: 0 })
		expect(paid.text()).toContain('Register Now')

		const free = mountOverlay({ allow_self_enrollment: 1, seat_count: 0 })
		expect(free.text()).toContain('Enroll Now')
	})
})
