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
vi.mock('@/components/InlineEdit/VideoLinkDialog.vue', () => ({
	default: {
		name: 'VideoLinkDialog',
		props: ['open', 'modelValue'],
		template: '<div />',
	},
}))
vi.mock('@framework/ui/telemetry/index', () => ({}))
const { resized } = vi.hoisted(() => ({
	resized: [] as ((entries: { contentRect: { width: number } }[]) => void)[],
}))
vi.mock('@vueuse/core', async (original) => ({
	...(await original<typeof import('@vueuse/core')>()),
	useResizeObserver: (_target: unknown, callback: typeof resized[0]) =>
		resized.push(callback),
}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({}))

import DraftCourseOutline from '@/components/Courses/DraftCourseOutline.vue'
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

	it('refits its height when its width changes', () => {
		const wrapper = mount(InlineText, {
			props: { modelValue: 'A long title', placeholder: 'Title' },
		})
		const field = wrapper.get('textarea').element
		Object.defineProperty(field, 'scrollHeight', { value: 33 })
		resized.at(-1)!([{ contentRect: { width: 800 } }])
		expect(field.style.height).toBe('35px')
		field.style.height = '64px'
		resized.at(-1)!([{ contentRect: { width: 800 } }])
		expect(field.style.height).toBe('64px')
	})
})

describe('the draft course outline', () => {
	it('keeps a row field clear of its icon but its text in the icon column', () => {
		const wrapper = mount(DraftCourseOutline, {
			props: { modelValue: [{ title: 'Basics', lessons: ['Setup'] }] },
			...options,
		})
		// The row gap is 8px: a 4px pull leaves 4px before the border, and
		// border plus 3px padding puts the text back 8px from the icon.
		for (const field of wrapper.findAll('textarea')) {
			expect(field.classes()).toEqual(
				expect.arrayContaining(['-ms-1', 'ps-[3px]'])
			)
			expect(field.classes()).not.toContain('-ms-[11px]')
		}
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

	it('names the choice in its menu and leaves the price to the field', () => {
		const wrapper = mountPrice({ paid: true, currency: 'INR', amount: 500 })
		expect(wrapper.findComponent(PriceInput).props('amount')).toBe(500)
		expect(wrapper.get('button').text()).toBe('Paid')
		const free = mountPrice({ paid: false })
		expect(free.get('button').text()).toBe('Free')
	})

	it('emits the amount as a number', async () => {
		const wrapper = mount(PriceInput, options)
		await wrapper
			.findComponent({ name: 'FormControl' })
			.vm.$emit('update:modelValue', '42')
		expect(wrapper.emitted('update:amount')).toEqual([[42]])
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
