import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import CertificateStack from '@/components/Certificates/CertificateStack.vue'

const certificates = [
	{ name: 'newest', title: 'ERPNext' },
	{ name: 'middle', title: 'Frappe Framework' },
	{ name: 'oldest', title: 'Python' },
]

const mountStack = (props: Record<string, unknown> = {}) =>
	mount(CertificateStack, {
		props: { certificates, ...props },
		global: {
			stubs: {
				CertificateThumbnail: {
					props: ['certificate'],
					template: '<div data-thumbnail>{{ certificate }}</div>',
				},
			},
		},
	})

/** Certificate names from the top sheet to the back one. */
const order = (wrapper: ReturnType<typeof mountStack>) =>
	wrapper
		.findAll('[data-sheet]')
		.map((sheet, index) => ({
			name: certificates[index].name,
			position: Number(sheet.attributes('data-position')),
			zIndex: Number((sheet.element as HTMLElement).style.zIndex),
		}))
		.sort((a, b) => a.position - b.position)

const mockReducedMotion = (matches: boolean) =>
	vi.stubGlobal(
		'matchMedia',
		vi.fn(() => ({
			matches,
			addEventListener: vi.fn(),
			removeEventListener: vi.fn(),
		}))
	)

describe('CertificateStack', () => {
	beforeEach(() => {
		vi.useFakeTimers()
		mockReducedMotion(false)
	})

	afterEach(() => {
		vi.useRealTimers()
		vi.unstubAllGlobals()
	})

	it('puts the latest certificate on top', () => {
		const sheets = order(mountStack())
		expect(sheets.map((sheet) => sheet.name)).toEqual([
			'newest',
			'middle',
			'oldest',
		])
		expect(sheets[0].zIndex).toBeGreaterThan(sheets[1].zIndex)
		expect(sheets[1].zIndex).toBeGreaterThan(sheets[2].zIndex)
	})

	it('renders the real preview only for the top sheet until played', async () => {
		const wrapper = mountStack()
		expect(wrapper.findAll('[data-thumbnail]').map((t) => t.text())).toEqual([
			'newest',
		])
		await wrapper.setProps({ playing: true })
		expect(wrapper.findAll('[data-thumbnail]')).toHaveLength(3)
	})

	it('cycles through the certificates while playing', async () => {
		const wrapper = mountStack()
		await wrapper.setProps({ playing: true })
		vi.advanceTimersByTime(1300)
		await nextTick()
		expect(order(wrapper)[0].name).toBe('middle')
		vi.advanceTimersByTime(1300)
		await nextTick()
		expect(order(wrapper)[0].name).toBe('oldest')
		vi.advanceTimersByTime(1300)
		await nextTick()
		expect(order(wrapper)[0].name).toBe('newest')
	})

	it('returns to the latest on top when it stops', async () => {
		const wrapper = mountStack()
		await wrapper.setProps({ playing: true })
		vi.advanceTimersByTime(1300)
		await wrapper.setProps({ playing: false })
		expect(order(wrapper)[0].name).toBe('newest')
		vi.advanceTimersByTime(5000)
		await nextTick()
		expect(order(wrapper)[0].name).toBe('newest')
	})

	it('stays still when the user prefers reduced motion', async () => {
		mockReducedMotion(true)
		const wrapper = mountStack()
		await wrapper.setProps({ playing: true })
		vi.advanceTimersByTime(5000)
		await nextTick()
		expect(order(wrapper)[0].name).toBe('newest')
	})

	it('shows a single sheet for one certificate', async () => {
		const wrapper = mountStack({ certificates: [certificates[0]] })
		await wrapper.setProps({ playing: true })
		vi.advanceTimersByTime(5000)
		expect(wrapper.findAll('[data-sheet]')).toHaveLength(1)
	})
})
