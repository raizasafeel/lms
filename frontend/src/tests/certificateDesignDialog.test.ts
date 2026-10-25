import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CertificateDesignDialog from '@/components/Modals/CertificateDesignDialog.vue'
import CertificatePreview from '@/components/CertificatePreview.vue'
import { describeDesign, sortDesigns } from '@/utils/certificateDesigns'

interface FakeResource {
	url: string
	data: unknown
	loading: boolean
	reload: ReturnType<typeof vi.fn>
	makeParams?: () => unknown
}

const { resources } = vi.hoisted(() => ({
	resources: {} as Record<string, FakeResource>,
}))

vi.mock('frappe-ui', () => ({
	Badge: { template: '<span data-badge><slot /></span>' },
	Button: {
		props: ['disabled'],
		template: '<button :disabled="disabled"><slot /></button>',
	},
	Dialog: {
		props: ['open'],
		template:
			'<div v-if="open" role="dialog"><slot /><slot name="actions" /></div>',
	},
	RadioGroup: {
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template: '<div role="radiogroup"><slot /></div>',
	},
	Radio: {
		props: ['value'],
		template:
			'<button role="radio" :data-value="value" @click="$parent.$emit(\'update:modelValue\', value)"><slot name="label" /></button>',
	},
	Switch: {
		props: ['modelValue', 'label'],
		emits: ['update:modelValue'],
		template:
			'<button :data-switch="label" @click="$emit(\'update:modelValue\', !modelValue)" />',
	},
	createResource: (options: { url: string; makeParams?: () => unknown }) => {
		const resource: FakeResource = {
			...options,
			data: null,
			loading: false,
			reload: vi.fn(),
		}
		if (options.url === 'lms.lms.api.get_certificate_designs') {
			resource.data = {
				designs: ['Certificate Modern', 'My Custom', 'Certificate'],
				default: 'Certificate',
			}
		}
		resources[options.url] = resource
		return resource
	},
}))

vi.stubGlobal('__', (s: string) => s)
if (!String.prototype.format) {
	String.prototype.format = function (this: string, ...args: string[]) {
		return this.replace(
			/{(\d+)}/g,
			(_: string, i: string) => args[Number(i)] ?? ''
		)
	}
}

function mountDialog(current: string | null = null) {
	return mount(CertificateDesignDialog, {
		props: { open: true, course: 'C1', courseTitle: 'Data', current },
		global: {
			mocks: { __: (s: string) => s },
			stubs: { CertificatePreview: true },
		},
	})
}

const PREVIEW = 'lms.lms.api.preview_certificate_template'

describe('CertificateDesignDialog', () => {
	beforeEach(() => {
		for (const key of Object.keys(resources)) delete resources[key]
	})

	it('lists the original design first and custom designs last', () => {
		const wrapper = mountDialog()
		const values = wrapper
			.findAll('[role="radio"]')
			.map((radio) => radio.attributes('data-value'))
		expect(values).toEqual(['Certificate', 'Certificate Modern', 'My Custom'])
	})

	it('marks the design in use and offers Done while it is selected', () => {
		const wrapper = mountDialog('Certificate Modern')
		const modern = wrapper.find('[data-value="Certificate Modern"]')
		expect(modern.find('[data-badge]').text()).toBe('In use')
		expect(wrapper.text()).toContain('Done')
	})

	it('falls back to the site default as the design in use', () => {
		const wrapper = mountDialog(null)
		expect(
			wrapper.find('[data-value="Certificate"] [data-badge]').exists()
		).toBe(true)
	})

	it('names the act and emits the new design', async () => {
		const wrapper = mountDialog('Certificate')
		await wrapper.find('[data-value="Certificate Modern"]').trigger('click')
		const confirm = wrapper
			.findAll('button')
			.find((b) => b.text() === 'Use Modern')
		expect(confirm).toBeDefined()
		await confirm!.trigger('click')
		expect(wrapper.emitted('select')).toEqual([['Certificate Modern']])
		expect(wrapper.emitted('update:open')).toEqual([[false]])
	})

	it('emits nothing when the design in use is confirmed', async () => {
		const wrapper = mountDialog('Certificate')
		await wrapper
			.findAll('button')
			.find((b) => b.text() === 'Done')!
			.trigger('click')
		expect(wrapper.emitted('select')).toBeUndefined()
	})

	it('previews the selected design with the chosen sample data', async () => {
		const wrapper = mountDialog('Certificate')
		await wrapper.find('[data-switch="Arabic (RTL)"]').trigger('click')
		await flushPromises()
		expect(resources[PREVIEW]!.reload).toHaveBeenCalled()
		expect(resources[PREVIEW]!.makeParams?.()).toEqual({
			print_format: 'Certificate',
			course: 'C1',
			sample: JSON.stringify({
				long: false,
				batch: false,
				expiry: false,
				no_logo: false,
				rtl: true,
			}),
		})
	})
})

describe('CertificatePreview', () => {
	it('renders the certificate in a fully sandboxed frame', () => {
		const wrapper = mount(CertificatePreview, {
			props: { html: '<p>cert</p>', title: 'Preview' },
			global: { mocks: { __: (s: string) => s } },
		})
		const frame = wrapper.find('iframe')
		expect(frame.attributes('sandbox')).toBe('')
		expect(frame.attributes('srcdoc')).toBe('<p>cert</p>')
		expect(frame.attributes('title')).toBe('Preview')
	})

	it('says when a design has nothing to show', () => {
		const wrapper = mount(CertificatePreview, {
			props: { html: null, title: 'Preview' },
			global: { mocks: { __: (s: string) => s } },
		})
		expect(wrapper.find('iframe').exists()).toBe(false)
		expect(wrapper.text()).toContain('Preview unavailable')
	})
})

describe('certificate design metadata', () => {
	it('describes shipped designs with a thumbnail and custom ones without', () => {
		expect(describeDesign('Certificate').label).toBe('Original')
		expect(describeDesign('Certificate Ledger').thumbnail).toBe(
			'/assets/lms/images/certificates/ledger.png'
		)
		expect(describeDesign('Acme').thumbnail).toBeNull()
		expect(describeDesign('Acme').description).toBe('Custom template')
	})

	it('sorts custom designs alphabetically after the shipped ones', () => {
		expect(sortDesigns(['Zeta', 'Certificate Record', 'Alpha'])).toEqual([
			'Certificate Record',
			'Alpha',
			'Zeta',
		])
	})
})
