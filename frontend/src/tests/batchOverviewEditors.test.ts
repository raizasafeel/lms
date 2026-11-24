import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.stubGlobal('__', (text: string) => text)
// translation.js installs String.prototype.format at app boot.
String.prototype.format = function (this: string, ...args: unknown[]): string {
	return args.reduce<string>(
		(out, arg, i) => out.replaceAll(`{${i}}`, String(arg)),
		this
	)
}

const { callMock, field, choices } = vi.hoisted(() => ({
	choices: [
		{ name: 'Q1', title: 'Accounting quiz', passing_percentage: 70 },
		{ name: 'Q2', title: 'Stock quiz' },
	],
	callMock: vi.fn(),
	field: (name: string) => ({
		name,
		props: ['modelValue', 'options', 'variant', 'placeholder'],
		template: '<div><slot name="prefix" /></div>',
	}),
}))

vi.mock('frappe-ui', () => ({
	Button: {
		props: ['label'],
		template: '<button><slot />{{ label }}</button>',
	},
	call: callMock,
	Combobox: { ...field('Combobox'), methods: { focus: () => {} } },
	createListResource: () => ({ data: null }),
	createResource: (resource: { url: string }) => ({
		data: resource.url === 'lms.lms.utils.get_assessments' ? [] : choices,
		fetched: true,
		reload: vi.fn(),
		loading: false,
	}),
	DatePicker: field('DatePicker'),
	DateRangePicker: field('DateRangePicker'),
	FormControl: field('FormControl'),
	Select: field('Select'),
	Switch: field('Switch'),
	TimePicker: field('TimePicker'),
	toast: { error: vi.fn(), success: vi.fn() },
}))
vi.mock('@/utils', () => ({
	formatNumberIntoCurrency: (amount: number, currency: string) =>
		amount ? `${currency} ${amount}` : '',
}))
vi.mock('@/components/InlineEdit/PickerDialog.vue', () => ({
	default: {
		name: 'PickerDialog',
		props: ['open', 'title', 'items', 'createLabel', 'categories'],
		emits: ['add', 'create', 'update:open'],
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
vi.mock('@/components/VideoPreview.vue', () => ({
	default: {
		name: 'VideoPreview',
		props: ['videoLink', 'fallbackImage'],
		template: '<div />',
	},
}))
vi.mock('@/components/InlineEdit/PriceInput.vue', () => ({
	default: { name: 'PriceInput', template: '<div />' },
}))

import BatchAssessmentList from '@/pages/Batches/components/overview/BatchAssessmentList.vue'
import BatchAssessmentAdd from '@/pages/Batches/components/overview/BatchAssessmentAdd.vue'
import BatchEnrollCardEditor from '@/pages/Batches/components/overview/BatchEnrollCardEditor.vue'
import CategoryFilter from '@/components/Controls/CategoryFilter.vue'
import TimeRangeField from '@/components/InlineEdit/TimeRangeField.vue'
import BatchFactsEditor from '@/pages/Batches/components/overview/BatchFactsEditor.vue'

const form = { isMissing: () => false }
const options = { global: { mocks: { __: globalThis.__ } } }

const mountCard = (doc: Record<string, unknown>, studentCount?: number) =>
	mount(BatchEnrollCardEditor, {
		props: { doc, form, studentCount } as never,
		...options,
	})

describe('the batch enroll card editor', () => {
	it('has no cover image field', () => {
		const html = mountCard({}).html()
		expect(html).not.toContain('ImageField')
		expect(mountCard({}).text()).not.toContain('This batch includes')
	})

	it('sets the preview video under the details, above the enroll button', async () => {
		const doc: Record<string, unknown> = { meta_image: '/files/m.png' }
		const card = mountCard(doc)
		const text = card.text()
		expect(text.indexOf('Add preview video')).toBeLessThan(
			text.indexOf('Contact the Administrator')
		)
		const dialog = card.findComponent({ name: 'VideoLinkDialog' })
		const button = card
			.findAll('button')
			.find((each) => each.text() === 'Add preview video')
		await button?.trigger('click')
		expect(dialog.props('open')).toBe(true)
		dialog.vm.$emit('update:modelValue', 'https://youtu.be/x')
		expect(doc.video_link).toBe('https://youtu.be/x')
	})

	it('previews a set video with the meta image as its poster', () => {
		const card = mountCard({
			video_link: 'https://youtu.be/x',
			meta_image: '/files/m.png',
		})
		const preview = card.findComponent({ name: 'VideoPreview' })
		expect(preview.props()).toEqual({
			videoLink: 'https://youtu.be/x',
			fallbackImage: '/files/m.png',
		})
		expect(card.text()).toContain('Change video')
	})

	it('names the formatted price on a paid batch', () => {
		const card = mountCard({ paid_batch: 1, amount: 30000, currency: 'INR' })
		expect(card.text()).toContain('Enroll for INR 30000')
		expect(card.text()).not.toContain('Learners see this button.')
	})

	it('reads Enroll on a free self-enroll batch, else the contact message', () => {
		expect(mountCard({ allow_self_enrollment: 1 }).text()).toContain('Enroll')
		expect(mountCard({}).text()).toContain('Contact the Administrator')
	})
})

describe('the batch facts editor', () => {
	const mountFacts = (doc: Record<string, unknown>, studentCount?: number) =>
		mount(BatchFactsEditor, {
			props: { doc, form, studentCount } as never,
			...options,
		})

	it('draws every field as a ghost field', () => {
		const facts = mountFacts({ evaluation: 1 })
		for (const name of ['DateRangePicker', 'Select']) {
			expect(facts.findComponent({ name }).props('variant')).toBe('ghost')
		}
	})

	it('leaves the book-by date to batch settings', () => {
		const facts = mountFacts({ evaluation: 1 })
		expect(facts.findComponent({ name: 'DatePicker' }).exists()).toBe(false)
		expect(facts.text()).not.toContain('Book by')
	})

	it('sets class times through the shared time range field', () => {
		const range = mountFacts({ start_time: '10:00:00' }).findComponent(
			TimeRangeField
		)
		expect(range.props('start')).toBe('10:00:00')
	})

	it('counts the seats left once a limit is set', () => {
		expect(mountFacts({ seat_count: 20 }, 18).text()).toContain(
			'seats · 2 left'
		)
		expect(mountFacts({ seat_count: 20 }).text()).toContain('seats')
		expect(mountFacts({}).text()).toContain('No seat limit')
	})

	it('says Zoom only when the batch has a Zoom account', () => {
		const labels = (doc: Record<string, unknown>) =>
			mountFacts(doc)
				.findComponent({ name: 'Select' })
				.props('options')
				.map((option: { label: string }) => option.label)
		expect(labels({})).toContain('Online')
		expect(labels({ zoom_account: 'Z1' })).toContain('Online on Zoom')
	})

	// Each icon sits in its field's prefix, so every hover box starts at the
	// card edge and every value at the prefix text column.
	it('draws each fact icon inside its field', () => {
		const facts = mountFacts({ evaluation: 1, certification: 1 })
		for (const name of ['DateRangePicker', 'Combobox', 'FormControl']) {
			const control = facts.findComponent({ name })
			expect(control.find('.size-4').exists()).toBe(true)
			expect(control.element.parentElement?.className).not.toContain('ps-2')
		}
		const medium = facts
			.findAllComponents({ name: 'Select' })
			.find((select) => select.attributes('aria-label') === 'Medium')!
		expect(medium.find('.lucide-video').exists()).toBe(true)
		expect(facts.findComponent(TimeRangeField).classes()).not.toContain('-ms-2')
	})
})

describe('the assessment add button', () => {
	beforeEach(() => callMock.mockReset())

	const openPicker = async () => {
		const row = mount(BatchAssessmentAdd, {
			props: { batchName: 'B1', added: ['LMS Quiz::Q2'] },
			...options,
		})
		await row.find('button').trigger('click')
		return { row, dialog: row.findComponent({ name: 'PickerDialog' }) }
	}

	it('is one button that opens one picker for every type', async () => {
		const { row, dialog } = await openPicker()
		expect(row.findAll('button').map((b) => b.text())).toEqual([
			'Add assessment',
		])
		expect(dialog.props('open')).toBe(true)
		expect(dialog.props('createLabel')).toBeUndefined()
		expect(dialog.props('categories')).toEqual([
			'Quiz',
			'Assignment',
			'Programming exercise',
		])
	})

	it('lists each type, typed by category, leaving out ones already added', async () => {
		const items = (await openPicker()).dialog.props('items')
		expect(items.map((item: { value: string }) => item.value)).toEqual([
			'LMS Quiz::Q1',
			'LMS Assignment::Q1',
			'LMS Assignment::Q2',
			'LMS Programming Exercise::Q1',
			'LMS Programming Exercise::Q2',
		])
		expect(items[0]).toMatchObject({
			title: 'Accounting quiz',
			category: 'Quiz',
			icon: 'lucide-circle-help',
			meta: ['Quiz', 'Pass at 70%'],
		})
		expect(items[1]).toMatchObject({
			category: 'Assignment',
			icon: 'lucide-file-pen',
		})
	})

	it('adds every picked one through its own type', async () => {
		callMock.mockResolvedValue({})
		const { row, dialog } = await openPicker()
		dialog.vm.$emit('add', ['LMS Quiz::Q1', 'LMS Assignment::Q2'])
		await flushPromises()
		expect(callMock.mock.calls.map((call) => call[1].doc)).toEqual([
			{
				doctype: 'LMS Assessment',
				parent: 'B1',
				parenttype: 'LMS Batch',
				parentfield: 'assessment',
				assessment_type: 'LMS Quiz',
				assessment_name: 'Q1',
			},
			expect.objectContaining({
				assessment_type: 'LMS Assignment',
				assessment_name: 'Q2',
			}),
		])
		expect(row.emitted('added')).toHaveLength(1)
	})
})

describe('assessments on a batch not saved yet', () => {
	beforeEach(() => callMock.mockReset())

	it('hands the picks back with their titles instead of inserting them', async () => {
		const row = mount(BatchAssessmentAdd, { props: { added: [] }, ...options })
		await row.find('button').trigger('click')
		row
			.findComponent({ name: 'PickerDialog' })
			.vm.$emit('add', ['LMS Quiz::Q1'])
		await flushPromises()
		expect(callMock).not.toHaveBeenCalled()
		expect(row.emitted('picked')).toEqual([
			[
				[
					{
						name: 'LMS Quiz::Q1',
						assessment_type: 'LMS Quiz',
						assessment_name: 'Q1',
						title: 'Accounting quiz',
					},
				],
			],
		])
	})

	it('lists and removes the picks the page keeps', async () => {
		const draft = [
			{
				name: 'LMS Quiz::Q1',
				assessment_type: 'LMS Quiz' as const,
				assessment_name: 'Q1',
				title: 'Accounting quiz',
			},
		]
		const list = mount(BatchAssessmentList, {
			props: {
				draft,
				'onUpdate:draft': (rows: typeof draft) =>
					list.setProps({ draft: rows }),
			},
			global: {
				mocks: { __: globalThis.__ },
				stubs: { RouterLink: { template: '<a><slot /></a>' } },
			},
		})
		expect(list.text()).toContain('Accounting quiz')
		const remove = list
			.findAll('button')
			.find((b) => b.text() === 'Remove Accounting quiz')
		await remove!.trigger('click')
		expect(list.props('draft')).toEqual([])
		expect(callMock).not.toHaveBeenCalled()
	})
})

describe('the empty assessments list', () => {
	it('is one call to action with a single add button', () => {
		const list = mount(BatchAssessmentList, {
			props: { batchName: 'B1' },
			global: { mocks: { __: globalThis.__ }, stubs: { RouterLink: true } },
		})
		expect(list.text()).toContain('No assessments yet')
		const buttons = list.findAll('button').map((b) => b.text())
		expect(buttons).toEqual(['Add assessment'])
	})
})

describe('the picker filter', () => {
	it('can name its no-filter option for something other than categories', () => {
		const filter = mount(CategoryFilter, {
			props: { categories: ['Quiz'], allLabel: 'All types' },
			...options,
		})
		const labels = filter
			.findComponent({ name: 'Combobox' })
			.props('options')
			.map((option: { label: string }) => option.label)
		expect(labels).toEqual(['All types', 'Quiz'])
	})
})
