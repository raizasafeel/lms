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
	Alert: {
		props: ['title', 'description'],
		template: `<div class="alert">{{ title }} {{ description }}</div>`,
	},
	Button: {
		inheritAttrs: false,
		props: ['route'],
		template: `<button v-bind="$attrs"><slot /></button>`,
	},
}))

vi.mock('@/utils', () => ({
	formatNumberIntoCurrency: (amount: number, currency: string) =>
		`${currency} ${amount}`,
	formatTime: (time: string) => time,
	getFormattedDateRange: () => '',
}))

vi.mock('@/utils/timezone', () => ({
	formatTimezone: () => '',
	nextOccurrence: () => null,
}))

vi.mock('@/components/VideoPreview.vue', () => ({
	default: {
		props: ['videoLink', 'fallbackImage'],
		template: '<div class="video-preview">{{ videoLink }}</div>',
	},
}))
vi.mock('@/pages/Batches/components/overview/BatchFacts.vue', () => ({
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

// get_batch_details answers with the price for the learner's billing region.
describe('the batch price a learner sees', () => {
	it('shows the price in the currency the server resolved', () => {
		const w = mountOverlay({ paid_batch: 1, amount: 3210, currency: 'INR' })
		expect(w.text()).toContain('INR 3210')
	})

	it('strikes through the regular price a regional one replaces', () => {
		const w = mountOverlay({
			paid_batch: 1,
			amount: 30,
			currency: 'USD',
			regular_price: '$ 50',
		})
		expect(w.get('[data-testid="regular-price"]').text()).toContain('$ 50')
	})

	it('shows no regular price when the learner pays it', () => {
		const w = mountOverlay({ paid_batch: 1, amount: 50, currency: 'USD' })
		expect(w.find('[data-testid="regular-price"]').exists()).toBe(false)
	})

	it('calls a free batch free', () => {
		const w = mountOverlay({ paid_batch: 0, amount: 3210, currency: 'INR' })
		expect(w.text()).toContain('Free')
		expect(w.text()).not.toContain('INR')
	})
})
