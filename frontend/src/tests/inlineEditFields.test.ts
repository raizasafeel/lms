import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.hoisted(() => {
	// @/utils pulls in plyr, which touches matchMedia at import time.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

vi.mock('frappe-ui', () => ({
	Button: { template: '<button><slot /></button>' },
	FileUploader: {
		template:
			'<div><slot :openFileSelector="() => {}" :uploading="false" /></div>',
	},
	FormControl: {
		name: 'FormControl',
		props: ['variant'],
		template: '<input />',
	},
	Popover: { template: '<div><slot name="trigger" /></div>' },
	Select: {
		name: 'Select',
		props: ['modelValue', 'options', 'variant'],
		template: '<div />',
	},
	UploadError: class extends Error {},
	toast: { error: vi.fn() },
}))
vi.mock('@/components/RichTextEditor.vue', () => ({
	default: {
		name: 'RichTextEditor',
		props: {
			menuOnFocus: Boolean,
			variant: String,
			toolbar: Array,
			ariaInvalid: Boolean,
		},
		template: '<div />',
	},
}))
vi.mock('@/components/Controls/VideoPreviewField.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@framework/ui/telemetry/index', () => ({}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({}))

import ImageField from '@/components/InlineEdit/ImageField.vue'
import InlineText from '@/components/InlineEdit/InlineText.vue'
import PriceField from '@/components/InlineEdit/PriceField.vue'
import PriceInput from '@/components/InlineEdit/PriceInput.vue'
import RichTextField from '@/components/InlineEdit/RichTextField.vue'

const options = {
	global: { mocks: { __: globalThis.__ }, stubs: { Link: true } },
}

describe('the inline text field', () => {
	it('draws frappe-ui outline chrome and rings when missing', async () => {
		const wrapper = mount(InlineText, {
			props: { modelValue: 'Data', placeholder: 'Title' },
		})
		const field = wrapper.get('textarea')
		expect(field.classes()).toEqual(
			expect.arrayContaining(['border', 'border-outline-gray-2'])
		)
		expect(field.classes()).not.toContain('ring-outline-red-3')
		await wrapper.setProps({ missing: true })
		expect(field.classes()).toContain('ring-outline-red-3')
	})

	it('hands Enter to the next field instead of a newline', async () => {
		const wrapper = mount(InlineText, { props: { placeholder: 'Title' } })
		await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
		expect(wrapper.emitted('enter')).toHaveLength(1)
	})
})

describe('the price field', () => {
	const mountPrice = (props: Record<string, unknown>) =>
		mount(PriceField, { props: { label: 'Price', ...props }, ...options })

	it('reads Free and hides the amount until paid', () => {
		const wrapper = mountPrice({ paid: false })
		expect(wrapper.text()).toContain('Free')
		expect(wrapper.findComponent(PriceInput).exists()).toBe(false)
		expect(wrapper.findComponent({ name: 'Select' }).props('variant')).toBe(
			'outline'
		)
	})

	it('asks the parent to switch to paid', async () => {
		const wrapper = mountPrice({ paid: false })
		await wrapper
			.findComponent({ name: 'Select' })
			.vm.$emit('update:modelValue', 'paid')
		expect(wrapper.emitted('update:paid')).toEqual([[true]])
	})

	it('shows the price learners pay once set', () => {
		const wrapper = mountPrice({ paid: true, currency: 'INR', amount: 500 })
		expect(wrapper.findComponent(PriceInput).exists()).toBe(true)
		expect(wrapper.text()).toContain('500')
	})

	it('emits the amount as a number', async () => {
		const wrapper = mount(PriceInput, options)
		await wrapper
			.findComponent({ name: 'FormControl' })
			.vm.$emit('update:modelValue', '42')
		expect(wrapper.emitted('update:amount')).toEqual([[42]])
	})
})

describe('the image field', () => {
	it('offers colour swatches for an empty course thumbnail', async () => {
		const wrapper = mount(ImageField, {
			props: { swatches: true, tint: 'Blue' },
			...options,
		})
		await wrapper.get('[aria-label="red thumbnail"]').trigger('click')
		expect(wrapper.emitted('update:tint')).toEqual([['Red']])
	})

	it('prompts for an image without swatches', () => {
		const wrapper = mount(ImageField, options)
		expect(wrapper.text()).toContain('Add an image')
		expect(wrapper.find('[aria-pressed]').exists()).toBe(false)
	})
})

describe('the rich text field', () => {
	it('uses the outline editor with a focus-only toolbar', () => {
		const wrapper = mount(RichTextField, {
			props: { placeholder: 'About', ariaLabelledby: 'about', missing: true },
			...options,
		})
		const editor = wrapper.findComponent({ name: 'RichTextEditor' })
		expect(editor.props('variant')).toBe('outline')
		expect(editor.props('menuOnFocus')).toBe(true)
		expect(editor.props('toolbar').length).toBeGreaterThan(5)
		expect(editor.props('ariaInvalid')).toBe(true)
		expect(editor.classes()).toContain('ring-outline-red-3')
	})
})
