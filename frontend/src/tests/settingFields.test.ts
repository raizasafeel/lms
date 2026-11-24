import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { call } = vi.hoisted(() => ({ call: vi.fn() }))

vi.mock('frappe-ui', () => ({
	call,
	Button: {
		name: 'Button',
		props: ['theme', 'variant', 'loading'],
		emits: ['click'],
		template: '<button @click="$emit(\'click\')"><slot /></button>',
	},
	FormControl: {
		name: 'FormControl',
		props: ['modelValue', 'type', 'variant'],
		template: '<input />',
	},
	Switch: {
		name: 'Switch',
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template:
			'<button role="switch" @click="$emit(\'update:modelValue\', !modelValue)" />',
	},
}))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: {
		name: 'Link',
		props: ['modelValue', 'filters', 'variant'],
		emits: ['update:modelValue'],
		template: '<div />',
	},
}))
vi.mock('@/components/InlineEdit/PickerDialog.vue', () => ({
	default: {
		name: 'PickerDialog',
		props: ['open', 'items', 'categories'],
		emits: ['add', 'update:open'],
		template: '<div />',
	},
}))
vi.mock('@/composables/useCoursePickerItems', async () => {
	const { ref } = await import('vue')
	return {
		useCoursePickerItems: () => ({
			items: ref([]),
			categories: ref([]),
			load: vi.fn(),
		}),
	}
})
vi.mock('@/components/CourseCard.vue', () => ({
	default: { name: 'CourseCard', props: ['course'], template: '<article />' },
}))

import SettingAction from '@/components/InlineEdit/SettingAction.vue'
import SettingField from '@/components/InlineEdit/SettingField.vue'
import SettingSwitch from '@/components/InlineEdit/SettingSwitch.vue'
import SearchPreview from '@/components/InlineEdit/SearchPreview.vue'
import RelatedCoursesEditor from '@/components/Courses/RelatedCoursesEditor.vue'

// frappe's translation layer patches String.prototype.format in at runtime.
String.prototype.format = function (this: string, ...args: unknown[]): string {
	return this.replace(/{(\d+)}/g, (match, index) =>
		args[Number(index)] === undefined ? match : String(args[Number(index)])
	)
}

const global = { mocks: { __: (text: string) => text } }

describe('the shared settings fields', () => {
	it('keeps a 0/1 field a number when switched', async () => {
		const wrapper = mount(SettingSwitch, {
			props: { label: 'Featured', modelValue: 0 },
			global,
		})
		await wrapper.get('[role="switch"]').trigger('click')
		expect(wrapper.emitted('update:modelValue')).toEqual([[1]])
	})

	it('puts a short input on the end and a textarea under the label', () => {
		const short = mount(SettingField, { props: { label: 'Keywords' }, global })
		const long = mount(SettingField, {
			props: { label: 'Description', type: 'textarea' },
			global,
		})
		const input = short.getComponent({ name: 'FormControl' })
		expect(input.props('variant')).toBe('outline')
		expect(input.element.closest('.shrink-0')).not.toBeNull()
		const textarea = long.getComponent({ name: 'FormControl' })
		expect(textarea.props('type')).toBe('textarea')
		expect(textarea.element.closest('.shrink-0')).toBeNull()
	})

	it('draws a danger action red and reports the click', async () => {
		const wrapper = mount(SettingAction, {
			props: { label: 'Delete course', action: 'Delete', danger: true },
			global,
		})
		const button = wrapper.getComponent({ name: 'Button' })
		expect(button.props('theme')).toBe('red')
		await button.trigger('click')
		expect(wrapper.emitted('click')).toHaveLength(1)
	})
})

describe('the search preview', () => {
	it('shows the address, title and description as a result would', () => {
		const wrapper = mount(SearchPreview, {
			props: {
				url: 'school.example/lms/courses/erpnext',
				title: 'ERPNext Essentials',
				description: 'Become a certified consultant.',
			},
			global,
		})
		expect(wrapper.text()).toContain('school.example/lms/courses/erpnext')
		expect(wrapper.text()).toContain('ERPNext Essentials')
		expect(wrapper.text()).toContain('Become a certified consultant.')
	})

	it('asks for a description while there is none', () => {
		const wrapper = mount(SearchPreview, { props: { url: 'x' }, global })
		expect(wrapper.text()).toContain('Add a description to show here.')
	})
})

describe('the related courses editor', () => {
	const mountEditor = (modelValue: string[]) =>
		mount(RelatedCoursesEditor, {
			props: {
				courseName: 'course-a',
				modelValue,
				'onUpdate:modelValue': (value: string[]) =>
					wrapper.setProps({ modelValue: value }),
			},
			global,
		})
	let wrapper: ReturnType<typeof mountEditor>

	it('shows each related course as its card', async () => {
		call.mockImplementation((_method, { course }) =>
			Promise.resolve({ name: course, title: course.toUpperCase() })
		)
		wrapper = mountEditor(['course-b'])
		await flushPromises()
		expect(
			wrapper.getComponent({ name: 'CourseCard' }).props('course')
		).toEqual({ name: 'course-b', title: 'COURSE-B' })
	})

	it('adds the courses picked in the dialog once, and removes one', async () => {
		wrapper = mountEditor(['course-b'])
		const dialog = wrapper.getComponent({ name: 'PickerDialog' })
		expect(dialog.props('open')).toBe(false)
		await wrapper.get('[data-testid="add-related-course"]').trigger('click')
		expect(dialog.props('open')).toBe(true)

		dialog.vm.$emit('add', ['course-c', 'course-b'])
		await flushPromises()
		expect(wrapper.props('modelValue')).toEqual(['course-b', 'course-c'])

		await wrapper
			.findAll('[data-testid="related-course"] button')[0]
			.trigger('click')
		expect(wrapper.props('modelValue')).toEqual(['course-c'])
	})
})
