import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { certification } = vi.hoisted(() => ({
	certification: { data: null as unknown },
}))

vi.mock('frappe-ui', () => ({
	Button: {
		props: ['route', 'variant'],
		template: `<button :data-route="JSON.stringify(route)"><slot name="prefix" /><slot /></button>`,
	},
	createResource: () => certification,
}))

import CertificationLinks from '@/components/CertificationLinks.vue'

const PRICE = '₹ 15,000'

const mountLinks = (
	data: Record<string, unknown>,
	userData: Record<string, unknown>,
	preview?: 'enrolled'
) => {
	certification.data = reactive({ paid_certificate: 1, ...data })
	return mount(CertificationLinks, {
		props: { courseName: 'COURSE-1', price: PRICE, preview },
		global: {
			provide: { $user: { data: userData } },
			mocks: { __: globalThis.__ },
		},
	})
}

const route = (wrapper: ReturnType<typeof mountLinks>) =>
	JSON.parse(wrapper.get('button').attributes('data-route')!)

describe('the certificate buy button', () => {
	it('sells the certificate to an enrolled learner', () => {
		const wrapper = mountLinks(
			{ membership: { name: 'ENR-1' } },
			{ name: 'learner', is_student: true }
		)
		expect(wrapper.text()).toContain(`Buy certificate · ${PRICE}`)
		expect(route(wrapper)).toEqual({
			name: 'Billing',
			params: { type: 'certificate', name: 'COURSE-1' },
		})
	})

	it('shows nothing to a moderator outside student view', () => {
		const wrapper = mountLinks({ membership: null }, { is_moderator: true })
		expect(wrapper.find('button').exists()).toBe(false)
	})

	it('shows a previewing moderator the learner button, kept in student view', () => {
		const wrapper = mountLinks(
			{ membership: null, certificate: { name: 'CERT-1' } },
			{ is_moderator: true },
			'enrolled'
		)
		expect(wrapper.text()).toContain(`Buy certificate · ${PRICE}`)
		expect(route(wrapper)).toEqual({
			name: 'Billing',
			params: { type: 'certificate', name: 'COURSE-1' },
			query: { studentView: 1 },
		})
	})
})
