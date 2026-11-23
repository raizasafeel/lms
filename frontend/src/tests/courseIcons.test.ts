import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

vi.mock('frappe-ui', () => ({
	Button: {
		props: ['label', 'tooltip', 'iconLeft'],
		emits: ['click'],
		template: '<button @click="$emit(\'click\')">{{ label }}</button>',
	},
	FileUploader: {
		name: 'FileUploader',
		props: ['private', 'fileTypes'],
		template:
			'<div><slot :openFileSelector="() => {}" :uploading="false" /></div>',
	},
	UploadError: class extends Error {},
	toast: { error: vi.fn() },
}))

import CourseIconPicker from '@/components/InlineEdit/CourseIconPicker.vue'
import CourseThumbnailPicker from '@/components/InlineEdit/CourseThumbnailPicker.vue'
import { COURSE_ICONS, courseIcon, shuffleThumbnail } from '@/utils/courseIcons'

declare const process: { cwd(): string }

const options = { global: { mocks: { __: globalThis.__ } } }

describe('course icons', () => {
	it('match the icons the LMS Course controller allows, in order', () => {
		const controller = readFileSync(
			resolve(process.cwd(), '../lms/lms/doctype/lms_course/lms_course.py'),
			'utf8'
		)
		const tuple = controller.match(/COURSE_ICONS = \(([\s\S]*?)\)/)![1]
		const pythonIcons = [...tuple.matchAll(/"([^"]+)"/g)].map((m) => m[1])
		expect(pythonIcons).toEqual(COURSE_ICONS)
		expect(COURSE_ICONS).toHaveLength(18)
	})

	it('falls back to the open book for an empty or unknown icon', () => {
		expect(courseIcon('rocket')).toBe('lucide-rocket')
		expect(courseIcon('')).toBe('lucide-book-open')
		expect(courseIcon(null)).toBe('lucide-book-open')
		expect(courseIcon('not-an-icon')).toBe('lucide-book-open')
	})

	it('shuffles to a stored colour and an allowed icon, never the same pair', () => {
		const random = vi.spyOn(Math, 'random')
		for (const value of [0, 0.5, 0.999]) {
			random.mockReturnValue(value)
			const next = shuffleThumbnail('Red', 'boxes')
			expect(COURSE_ICONS).toContain(next.icon)
			expect(next.color).toMatch(/^[A-Z][a-z]+$/)
			expect(`${next.color}/${next.icon}`).not.toBe('Red/boxes')
		}
		random.mockRestore()
	})
})

describe('the course icon picker', () => {
	it('marks the current icon and emits the one clicked', async () => {
		const wrapper = mount(CourseIconPicker, {
			props: { modelValue: 'rocket' },
			...options,
		})
		expect(wrapper.findAll('button')).toHaveLength(18)
		expect(
			wrapper.get('[aria-label="rocket"]').attributes('aria-pressed')
		).toBe('true')
		await wrapper.get('[aria-label="chart line"]').trigger('click')
		expect(wrapper.emitted('update:modelValue')).toEqual([['chart-line']])
	})

	it('reads an empty icon as the open book', () => {
		const wrapper = mount(CourseIconPicker, options)
		expect(
			wrapper.get('[aria-label="book open"]').attributes('aria-pressed')
		).toBe('true')
	})

	it('lays out nine columns when asked', () => {
		const wrapper = mount(CourseIconPicker, {
			props: { columns: 9 },
			...options,
		})
		expect(wrapper.classes()).toContain('grid-cols-9')
	})
})

describe('the course thumbnail picker', () => {
	const mountPicker = (props: Record<string, unknown> = {}) =>
		mount(CourseThumbnailPicker, {
			props: { tint: 'Red', icon: 'boxes', ...props },
			...options,
		})

	it('previews the tint and icon', () => {
		const preview = mountPicker().get('[data-testid="thumbnail-preview"]')
		expect(preview.classes()).toContain('bg-surface-red-2')
		expect(preview.find('.lucide-boxes').exists()).toBe(true)
	})

	it('shuffles both the colour and the icon', async () => {
		vi.spyOn(Math, 'random').mockReturnValue(0)
		const wrapper = mountPicker({ tint: 'Blue', icon: 'rocket' })
		await wrapper.get('button').trigger('click')
		expect(wrapper.emitted('update:tint')).toEqual([['Red']])
		expect(wrapper.emitted('update:icon')).toEqual([['boxes']])
		vi.restoreAllMocks()
	})

	it('picks a colour and an icon', async () => {
		const wrapper = mountPicker()
		await wrapper.get('[aria-label="teal thumbnail"]').trigger('click')
		await wrapper.get('[aria-label="globe"]').trigger('click')
		expect(wrapper.emitted('update:tint')).toEqual([['Teal']])
		expect(wrapper.emitted('update:icon')).toEqual([['globe']])
	})

	it('uploads a public image instead', () => {
		const wrapper = mountPicker()
		const uploader = wrapper.findComponent({ name: 'FileUploader' })
		expect(uploader.props('private')).toBe(false)
		expect(wrapper.text()).toContain('Upload an image instead')
		uploader.vm.$emit('success', { file_url: '/files/cover.png' })
		expect(wrapper.emitted('update:image')).toEqual([['/files/cover.png']])
	})
})
