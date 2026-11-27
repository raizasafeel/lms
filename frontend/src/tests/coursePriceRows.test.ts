import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

vi.mock('frappe-ui', () => ({
	toast: { error: vi.fn() },
}))
vi.mock('@/stores/settings', () => ({
	useSettings: () => ({ settings: { data: { is_payments_app_installed: 1 } } }),
}))
vi.mock('@/components/InlineEdit/PriceInput.vue', () => ({
	default: { name: 'PriceInput', template: '<div data-testid="price" />' },
}))

import CoursePriceRows from '@/pages/Courses/CoursePriceRows.vue'

function mountRows(doc: Record<string, unknown>) {
	const form = reactive({ resource: { doc }, markDirty: vi.fn() })
	const wrapper = mount(CoursePriceRows, {
		global: {
			provide: { courseForm: form },
			stubs: {
				SettingSwitch: {
					name: 'SettingSwitch',
					props: ['label', 'modelValue'],
					emits: ['update:modelValue'],
					template: `<section :data-label="label" />`,
				},
			},
			mocks: { __: (text: string) => text },
		},
	})
	return { wrapper, form }
}

const labels = (wrapper: ReturnType<typeof mount>) =>
	wrapper.findAll('section').map((row) => row.attributes('data-label'))

describe('the course price rows', () => {
	it('offers a paid certificate only while the course is free', () => {
		expect(labels(mountRows({ paid_course: 0 }).wrapper)).toEqual([
			'Paid course',
			'Paid certificate',
		])
		expect(labels(mountRows({ paid_course: 1 }).wrapper)).toEqual([
			'Paid course',
		])
	})

	it('asks for the certificate amount only once it is paid', () => {
		expect(
			mountRows({ paid_course: 0 }).wrapper.findAll('[data-testid="price"]')
		).toHaveLength(0)
		expect(
			mountRows({
				paid_course: 0,
				paid_certificate: 1,
			}).wrapper.findAll('[data-testid="price"]')
		).toHaveLength(1)
	})

	it('selling the certificate makes it the evaluated one', () => {
		const { wrapper, form } = mountRows({
			paid_course: 0,
			enable_certification: 1,
		})

		wrapper
			.findAllComponents({ name: 'SettingSwitch' })[1]
			.vm.$emit('update:modelValue', true)

		expect(form.resource.doc).toMatchObject({
			paid_certificate: 1,
			enable_certification: 0,
		})
		expect(form.markDirty).toHaveBeenCalled()
	})

	it('makes a paid course include its certificate', () => {
		const { wrapper, form } = mountRows({ paid_course: 0, paid_certificate: 1 })

		wrapper
			.findAllComponents({ name: 'SettingSwitch' })[0]
			.vm.$emit('update:modelValue', true)

		expect(form.resource.doc).toMatchObject({
			paid_course: 1,
			paid_certificate: 0,
		})
		expect(form.markDirty).toHaveBeenCalled()
	})
})
