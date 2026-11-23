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
	Button: {
		props: ['label'],
		template:
			'<button :aria-label="label"><slot name="icon" /><slot /></button>',
	},
	FileUploader: {
		template:
			'<div><slot :openFileSelector="() => {}" :uploading="false" /></div>',
	},
	FormControl: {
		name: 'FormControl',
		props: ['variant'],
		template: '<input />',
	},
	Dropdown: {
		name: 'Dropdown',
		props: ['options'],
		template: `<div><slot /><button
			v-for="option in options"
			:key="option.label"
			:data-testid="'option-' + option.label"
			@click="option.onClick()"
		>{{ option.label }}</button></div>`,
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
	it('shows no border until focused and rings when missing', async () => {
		const wrapper = mount(InlineText, {
			props: { modelValue: 'Data', placeholder: 'Title' },
		})
		const field = wrapper.get('textarea')
		expect(field.classes()).toEqual(
			expect.arrayContaining([
				'border-transparent',
				'focus:border-outline-gray-4',
			])
		)
		expect(field.classes()).not.toContain('border-outline-gray-2')
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

	it('reads Free once and hides the amount until paid', () => {
		const wrapper = mountPrice({ paid: false })
		expect(wrapper.get('button').text()).toBe('Free')
		expect(wrapper.findComponent(PriceInput).exists()).toBe(false)
	})

	it('asks the parent to switch to paid from the price menu', async () => {
		const wrapper = mountPrice({ paid: false })
		await wrapper.get('[data-testid="option-Paid"]').trigger('click')
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

	it('shows the course icon in the tint and on the icon button', () => {
		const wrapper = mount(ImageField, {
			props: { swatches: true, tint: 'Pink', icon: 'rocket' },
			...options,
		})
		expect(wrapper.findAll('.lucide-rocket')).toHaveLength(2)
		expect(wrapper.find('[aria-label="Thumbnail icon"]').exists()).toBe(true)
	})

	it('shuffles the colour and the icon together', async () => {
		vi.spyOn(Math, 'random').mockReturnValue(0)
		const wrapper = mount(ImageField, {
			props: { swatches: true, tint: 'Blue', icon: 'rocket' },
			...options,
		})
		await wrapper.get('[aria-label="Random colour and icon"]').trigger('click')
		expect(wrapper.emitted('update:tint')).toEqual([['Red']])
		expect(wrapper.emitted('update:icon')).toEqual([['boxes']])
		vi.restoreAllMocks()
	})

	it('hides the thumbnail tools once there is an image', () => {
		const wrapper = mount(ImageField, {
			props: { swatches: true, image: '/files/a.png' },
			...options,
		})
		expect(wrapper.find('[aria-label="Thumbnail icon"]').exists()).toBe(false)
		expect(wrapper.find('[aria-label="Random colour and icon"]').exists()).toBe(
			false
		)
	})

	it('prompts for an image without swatches', () => {
		const wrapper = mount(ImageField, options)
		expect(wrapper.text()).toContain('Add an image')
		expect(wrapper.find('[aria-pressed]').exists()).toBe(false)
		expect(wrapper.find('[aria-label="Thumbnail icon"]').exists()).toBe(false)
	})
})

describe('the rich text field', () => {
	it('uses the inline editor with a focus-only toolbar', () => {
		const wrapper = mount(RichTextField, {
			props: { placeholder: 'About', ariaLabelledby: 'about', missing: true },
			...options,
		})
		const editor = wrapper.findComponent({ name: 'RichTextEditor' })
		expect(editor.props('variant')).toBe('inline')
		expect(editor.props('menuOnFocus')).toBe(true)
		expect(editor.props('toolbar').length).toBeGreaterThan(5)
		expect(editor.props('ariaInvalid')).toBe(true)
		expect(editor.classes()).toContain('ring-outline-red-3')
	})
})
