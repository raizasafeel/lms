/** The avatar's "Open to Work" / "Hiring" indicator. */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { vi } from 'vitest'

window.__ = (text: string): string => text

vi.mock('frappe-ui', () => ({
	Avatar: {
		props: ['label', 'image', 'size'],
		template: `<div><slot name="indicator" /></div>`,
	},
	Tooltip: {
		props: ['text', 'side'],
		template: `<div><slot /></div>`,
	},
}))

import UserAvatar from '@/components/UserAvatar.vue'

const indicator = (openTo: string) =>
	mount(UserAvatar, {
		props: { user: { full_name: 'A', open_to: openTo } as any, size: '2xl' },
		global: { config: { globalProperties: { __: (s: string) => s } as any } },
	})

describe('UserAvatar indicator', () => {
	// Guards: open-to-work and hiring told apart by colour alone. Introduced in
	// #2468; test added with the a11y audit remediation.
	it.each([
		['Work', 'Open to Work', 'lucide-check'],
		['Hiring', 'Hiring', 'lucide-briefcase'],
	])(
		'names the %s chip in text and shape, not colour',
		(openTo, label, icon) => {
			const wrapper = indicator(openTo)

			expect(wrapper.get('[role="img"]').attributes('aria-label')).toBe(label)
			expect(wrapper.get(`.${icon}`).attributes('aria-hidden')).toBe('true')
		}
	)

	it('draws no dot without a status', () => {
		expect(indicator('').find('[role="img"]').exists()).toBe(false)
	})
})
