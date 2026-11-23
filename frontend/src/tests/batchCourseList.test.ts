import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive, defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.stubGlobal('__', (text: string) => text)

const { createResourceMock, sent } = vi.hoisted(() => ({
	createResourceMock: vi.fn(),
	sent: [] as Array<Record<string, unknown>>,
}))

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
	call: vi.fn(),
	toast: { success: vi.fn(), error: vi.fn() },
	Button: { template: `<button><slot /></button>` },
}))

const { inert } = vi.hoisted(() => ({
	inert: () => ({ default: { render: () => null } }),
}))
vi.mock('@/components/ProgressBar.vue', inert)
vi.mock('@/composables/useBatchForms', () => ({ openBatchForm: vi.fn() }))

import BatchCourseList from '@/pages/Batches/components/overview/BatchCourseList.vue'

type Options = {
	params?: Record<string, unknown>
	makeParams?: () => Record<string, unknown>
	auto?: boolean
}

const pending: Array<{ batch: unknown; resolve: () => void }> = []

// Mirrors frappe-ui: each fetch gets its own controller, abort() cancels the
// latest one, and an aborted fetch never assigns `data`.
const fakeResource = (options: Options) => {
	let controller = new AbortController()
	const resource = {
		data: null as unknown,
		abort: () => controller.abort(),
		reload: () => {},
	}
	resource.reload = () => {
		const params = options.makeParams
			? options.makeParams()
			: options.params ?? {}
		sent.push(params)
		controller = new AbortController()
		const { signal } = controller
		pending.push({
			batch: params.batch,
			resolve: () => {
				if (!signal.aborted) resource.data = [params.batch]
			},
		})
	}
	if (options.auto) resource.reload()
	return resource
}

const router = createRouter({
	history: createMemoryHistory(),
	routes: [{ path: '/', component: { render: () => null } }],
})

// Mounted through a parent so the test can move the page to another batch.
const mountList = (props: { batchName?: string }) =>
	mount(
		defineComponent({
			render: () => h(BatchCourseList, { batchName: props.batchName }),
		}),
		{
			global: { plugins: [router], mocks: { __: (t: string) => t } },
		}
	)

describe('BatchCourseList courses request', () => {
	beforeEach(() => {
		sent.length = 0
		pending.length = 0
		createResourceMock.mockReset()
		createResourceMock.mockImplementation(fakeResource)
	})

	// Regression: get_batch_courses sent with no batch, so no courses showed
	// (#3007, fixed in #3040).
	it('waits for the batch name instead of sending an empty request', async () => {
		const batch = reactive<{ batchName?: string }>({})
		mountList(batch)
		await flushPromises()
		expect(sent.filter((p) => !p.batch)).toEqual([])

		batch.batchName = 'B1'
		await flushPromises()
		expect(sent.at(-1)).toEqual({ batch: 'B1' })
	})

	it('fetches the new batch when the page moves to another batch', async () => {
		const batch = reactive<{ batchName?: string }>({ batchName: 'B1' })
		mountList(batch)
		await flushPromises()
		expect(sent.at(-1)).toEqual({ batch: 'B1' })

		batch.batchName = 'B2'
		await flushPromises()
		expect(sent.at(-1)).toEqual({ batch: 'B2' })
	})

	// Regression: a slow response for the previous batch overwrote the new
	// batch's courses (raised in review of #3040).
	it('ignores a late response for the batch the page has left', async () => {
		const batch = reactive<{ batchName?: string }>({ batchName: 'B1' })
		mountList(batch)
		await flushPromises()
		batch.batchName = 'B2'
		await flushPromises()

		const resource = createResourceMock.mock.results[0].value
		pending.find((p) => p.batch === 'B2')?.resolve()
		pending.find((p) => p.batch === 'B1')?.resolve()
		expect(resource.data).toEqual(['B2'])
	})
})
