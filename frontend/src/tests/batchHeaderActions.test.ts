import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.stubGlobal('__', (text: string) => text)

vi.mock('frappe-ui', () => ({
	Button: { template: '<button><slot /></button>' },
	Dropdown: { name: 'Dropdown', props: ['options'], template: '<div />' },
	Tooltip: { template: '<div><slot /></div>' },
}))
vi.mock('vue-router', () => ({
	useRoute: () => ({ hash: '' }),
	useRouter: () => ({}),
}))
vi.mock('@/components/HeaderButton.vue', () => ({
	default: { props: ['label'], template: '<button>{{ label }}</button>' },
}))
vi.mock('@/pages/Batches/components/BatchSaveButton.vue', () => ({
	default: { name: 'BatchSaveButton', template: '<button>Save</button>' },
}))
vi.mock('@/composables/useBatchForms', () => ({ openBatchForm: vi.fn() }))
vi.mock('@/utils/composables', async () => {
	const { ref } = await import('vue')
	return { useScreenSize: () => ({ isMobile: ref(false) }) }
})
vi.mock('@/pages/Batches/composables/useBatchForm', () => ({
	injectBatchForm: () => ({}),
}))
vi.mock('@/pages/Batches/composables/useBatchManage', () => ({
	injectBatchManage: () => ({
		publishing: () => false,
		togglePublish: vi.fn(),
		deleteBatch: vi.fn(),
		generateCertificates: vi.fn(),
	}),
}))

import BatchHeaderActions from '@/pages/Batches/components/BatchHeaderActions.vue'

const mountActions = (published: number) =>
	mount(BatchHeaderActions, {
		props: { tab: 'overview', batch: { data: { published } } } as never,
		global: { mocks: { __: globalThis.__ } },
	})

const menuLabels = (wrapper: ReturnType<typeof mountActions>) =>
	wrapper
		.findComponent({ name: 'Dropdown' })
		.props('options')
		.map((option: { label: string }) => option.label)

describe('the batch header actions', () => {
	it('shows Publish in the header for an unpublished batch', () => {
		const actions = mountActions(0)
		expect(actions.text()).toContain('Publish')
		expect(menuLabels(actions)).not.toContain('Unpublish batch')
	})

	it('keeps Unpublish in the options menu, not the header', () => {
		const actions = mountActions(1)
		expect(actions.text()).not.toContain('Publish')
		expect(menuLabels(actions)).toContain('Unpublish batch')
	})

	it('leaves Save to the tab bar on desktop', () => {
		const actions = mountActions(0)
		expect(actions.findComponent({ name: 'BatchSaveButton' }).exists()).toBe(
			false
		)
	})
})
