/**
 * The badge form: what it loads, what it lets you change, and when it saves.
 *
 * The masthead this replaces drew the Title and the Description as bare
 * borderless inputs — `border-0 bg-transparent p-0 focus:outline-none
 * focus:ring-0`, with the placeholder as their only label. On an existing badge
 * the placeholder never shows, so both read as a heading and a paragraph: no
 * box, no border, and no focus ring even once the caret is in them. There was
 * nothing on screen to say either one could be typed into, which is the
 * "we can't even edit the top part" report. They are ordinary labelled
 * FormControls now, and the first describe below is what keeps them that way.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { saveMock, reloadMock, listReload, remove, rows, toast, call } =
	vi.hoisted(() => ({
		saveMock: vi.fn(),
		reloadMock: vi.fn(),
		listReload: vi.fn(),
		remove: vi.fn(),
		rows: [] as any[],
		toast: { success: vi.fn(), error: vi.fn() },
		call: vi.fn(() => Promise.resolve({})),
	}))

vi.mock('frappe-ui', () => ({
	call,
	toast,
	Button: {
		props: ['label', 'variant', 'loading', 'disabled'],
		emits: ['click'],
		template: `<button
			:disabled="disabled"
			:data-variant="variant"
			@click="$emit('click')"
		>{{ label }}<slot /></button>`,
	},
	ErrorMessage: {
		props: ['message'],
		template: `<div data-testid="error">{{ message }}</div>`,
	},
	FileUploader: {
		props: ['fileTypes', 'uploadArgs', 'validateFile'],
		emits: ['success'],
		template: `<div>
			<slot :uploading="false" :progress="0" :openFileSelector="() => {}" />
			<button
				data-testid="uploaded"
				@click="$emit('success', { file_url: '/files/badge.png' })"
			/>
		</div>`,
	},
	// Renders what the real control renders and nothing the old markup did: a
	// real <label for> pointing at the box, and no suppressed focus ring.
	FormControl: {
		props: {
			modelValue: {},
			label: {},
			type: {},
			placeholder: {},
			// Boolean-typed, like the real control's: Vue casts a bare `required`
			// to true only for a prop it knows is a boolean.
			required: { type: Boolean },
		},
		emits: ['update:modelValue'],
		template: `<span :data-label="label" :data-required="required ? 'yes' : 'no'">
			<label :for="'in-' + label">{{ label }}</label>
			<input
				:id="'in-' + label"
				:type="type"
				:value="modelValue"
				:placeholder="placeholder"
				@input="$emit('update:modelValue', $event.target.value)"
			/>
		</span>`,
	},
	LoadingIndicator: { template: `<span data-testid="spinner" />` },
}))

vi.mock('@/components/Controls/BooleanSwitch.vue', () => ({
	default: {
		props: ['modelValue', 'label', 'size', 'description'],
		emits: ['update:modelValue'],
		template: `<div data-testid="switch" :data-value="String(modelValue)" />`,
	},
}))
vi.mock('@/components/Controls/CodeEditor.vue', () => ({
	default: {
		props: ['modelValue', 'label', 'description', 'type', 'required', 'height'],
		emits: ['update:modelValue'],
		template: `<button
			data-testid="code"
			:data-value="modelValue"
			@click="$emit('update:modelValue', 'doc.progress == 100')"
		/>`,
	},
}))
vi.mock('@/components/Controls/Select.vue', () => ({
	default: {
		props: ['modelValue', 'label', 'options', 'required'],
		emits: ['update:modelValue'],
		template: `<button
			:data-testid="'select-' + label"
			:data-value="modelValue"
			@click="$emit('update:modelValue', options[0].value)"
		/>`,
	},
}))
vi.mock('@/components/Layouts/settings/desktop/SettingsLayout.vue', () => ({
	default: {
		emits: ['save'],
		props: [
			'title',
			'showBack',
			'unsaved',
			'enabled',
			'saveLabel',
			'saving',
			'canSave',
			'saveTestid',
		],
		template: `<div :data-title="title" :data-unsaved="unsaved ? 'yes' : 'no'">
			<slot name="header-actions" /><button v-if="saveLabel" :data-testid="saveTestid" :disabled="!canSave" :data-loading="saving ? 'yes' : 'no'" @click="$emit('save')">{{ saveLabel }}</button><slot />
		</div>`,
	},
}))
vi.mock('@/components/Layouts/settings/desktop/SettingsList.vue', () => ({
	default: {
		props: ['title', 'columns', 'rows'],
		emits: ['new', 'rowClick', 'loadMore'],
		template: `<div data-testid="list">
			<button data-testid="new" @click="$emit('new')" />
			<button
				v-for="row in rows"
				:key="row.name"
				:data-testid="'row-' + row.name"
				@click="$emit('rowClick', row)"
			/>
		</div>`,
	},
}))

vi.mock('@/composables/useSettingsListResource', () => ({
	SETTINGS_PAGE_LENGTH: 13,
	useSettingsListResource: () => ({
		resource: {},
		search: '',
		rows,
		loading: false,
		hasNextPage: false,
		loadMore: vi.fn(),
		reload: listReload,
		applyFilters: vi.fn(),
		remove,
	}),
}))

// A stand-in for the document resource: it loads the row the page asks for,
// keeps the copy the server last sent, and calls itself dirty when the two
// differ — which is exactly what frappe-ui's own isDirty compares.
vi.mock('@/composables/useSettingsSource', async () => {
	const { computed, reactive, ref, watch } = await import('vue')
	return {
		NEW_RECORD: 'new',
		useSettingsSource: (_source: any, options: any) => {
			const doc = ref<any>(null)
			const original = ref<any>(null)
			const isNew = ref(false)

			watch(
				() => options.record?.value ?? null,
				(name: string | null) => {
					isNew.value = name === 'new'
					if (!name) {
						doc.value = null
						original.value = null
						return
					}
					const row = rows.find((item) => item.name === name)
					doc.value = isNew.value ? {} : { ...row }
					original.value = isNew.value ? null : { ...row }
				},
				{ immediate: true }
			)

			return reactive({
				doc,
				name: computed(() => options.record?.value ?? null),
				isNew,
				isDirty: computed(() =>
					isNew.value
						? false
						: JSON.stringify(doc.value) !== JSON.stringify(original.value)
				),
				loading: false,
				save: saveMock,
				reload: reloadMock,
			})
		},
	}
})

vi.mock('@/composables/useDirtyGuard', () => ({ useDirtyGuard: vi.fn() }))
vi.mock('@/utils', () => ({
	cleanError: (message: string) => String(message).replace(/<[^>]+>/g, ''),
	validateFile: vi.fn(),
}))
vi.mock('@/utils/safeUrl', () => ({ safeUrl: (url: string) => url }))

vi.stubGlobal('__', (text: string) => text)
;(String.prototype as any).format ??= function (...args: string[]) {
	return args.reduce((out, arg, i) => out.replace(`{${i}}`, arg), String(this))
}

import Badges from '@/components/Settings/Badges/Badges.vue'

const champion = {
	name: 'Champion',
	title: 'Champion',
	enabled: 1,
	description: 'Finished a course',
	image: '/files/champion.png',
	grant_only_once: 1,
	event: 'Value Change',
	reference_doctype: 'LMS Batch',
	condition: 'doc.status == "Complete"',
	user_field: 'owner',
	field_to_check: '',
}

const mountPage = () =>
	mount(Badges, {
		props: { label: 'Badges' },
		global: { mocks: { __: (text: string) => text } },
	})

type Wrapper = ReturnType<typeof mountPage>

const openBadge = async (wrapper: Wrapper, name = 'Champion') => {
	await wrapper.find(`[data-testid="row-${name}"]`).trigger('click')
	await flushPromises()
	return wrapper
}

const openNew = async (wrapper: Wrapper) => {
	await wrapper.find('[data-testid="new"]').trigger('click')
	await flushPromises()
	return wrapper
}

// Either control: Description is a textarea (the doctype's Small Text), the
// rest are inputs. Both halves are scoped to the testid — a bare `, textarea`
// would match any textarea on the page.
const control = (testid: string) =>
	`[data-testid="${testid}"] input, [data-testid="${testid}"] textarea`

const field = (wrapper: Wrapper, testid: string) => wrapper.get(control(testid))

const valueOf = (wrapper: Wrapper, testid: string) =>
	(wrapper.get(control(testid)).element as HTMLInputElement).value

const save = (wrapper: Wrapper) =>
	wrapper.get('[data-testid="badge-save"]').trigger('click')

beforeEach(() => {
	vi.clearAllMocks()
	rows.length = 0
	rows.push({ ...champion })
	saveMock.mockResolvedValue({ name: 'Champion' })
})

describe('the top of the badge form is editable', () => {
	it('takes what is typed into the Title', async () => {
		const wrapper = await openBadge(mountPage())

		await field(wrapper, 'badge-title').setValue('Course Champion')

		expect(valueOf(wrapper, 'badge-title')).toBe('Course Champion')
	})

	it('takes what is typed into the Description', async () => {
		const wrapper = await openBadge(mountPage())

		await field(wrapper, 'badge-description').setValue('Finished every lesson')

		expect(valueOf(wrapper, 'badge-description')).toBe('Finished every lesson')
	})

	// The bug was that neither said it was a field. Both are drawn by a control
	// that renders its own <label for> — not a placeholder standing in for one —
	// so the box is named on screen and by a screen reader alike.
	it('labels both of them on screen, pointing at the box', () => {
		const wrapper = mountPage()
		return openBadge(wrapper).then(() => {
			for (const [testid, text] of [
				['badge-title', 'Title'],
				['badge-description', 'Description'],
			]) {
				const control = wrapper.get(`[data-testid="${testid}"]`)
				expect(control.attributes('data-label')).toBe(text)
				const label = control.get('label')
				expect(label.text()).toBe(text)
				expect(label.attributes('for')).toBe(
					control.get('input').attributes('id')
				)
			}
		})
	})

	// A control with its focus ring taken away and nothing put back is a control
	// a keyboard user cannot find (WCAG 2.4.7). The old masthead did exactly
	// that, on both boxes.
	it('leaves every field its focus indicator', async () => {
		const wrapper = await openBadge(mountPage())

		const html = wrapper.get('[data-testid="badge-fields"]').html()

		expect(html).not.toContain('focus:outline-none')
		expect(html).not.toContain('focus:ring-0')
	})

	it('marks both of them required, as LMS Badge does', async () => {
		const wrapper = await openBadge(mountPage())

		expect(
			wrapper.get('[data-testid="badge-title"]').attributes('data-required')
		).toBe('yes')
		expect(
			wrapper
				.get('[data-testid="badge-description"]')
				.attributes('data-required')
		).toBe('yes')
	})

	it('uploads a new picture onto the badge', async () => {
		const wrapper = await openBadge(mountPage())

		await wrapper.get('[data-testid="uploaded"]').trigger('click')

		expect(
			wrapper.get('[data-testid="badge-image"] img').attributes('src')
		).toBe('/files/badge.png')
	})
})

describe('opening a badge', () => {
	it('fills every field from the record', async () => {
		const wrapper = await openBadge(mountPage())

		expect(valueOf(wrapper, 'badge-title')).toBe('Champion')
		expect(valueOf(wrapper, 'badge-description')).toBe('Finished a course')
		expect(
			wrapper.get('[data-testid="select-Assign For"]').attributes('data-value')
		).toBe('LMS Batch')
		expect(
			wrapper.get('[data-testid="select-Assign To"]').attributes('data-value')
		).toBe('owner')
		expect(
			wrapper.get('[data-testid="select-Event"]').attributes('data-value')
		).toBe('Value Change')
		expect(wrapper.get('[data-testid="code"]').attributes('data-value')).toBe(
			'doc.status == "Complete"'
		)
		expect(
			wrapper.get('[data-testid="badge-image"] img').attributes('src')
		).toBe('/files/champion.png')
	})

	it('titles the page with the badge it opened', async () => {
		const wrapper = await openBadge(mountPage())

		expect(wrapper.get('[data-title]').attributes('data-title')).toBe(
			'Champion'
		)
	})

	it('opens a new badge on the doctype defaults', async () => {
		const wrapper = await openNew(mountPage())

		expect(wrapper.get('[data-title]').attributes('data-title')).toBe(
			'New Badge'
		)
		expect(valueOf(wrapper, 'badge-title')).toBe('')
		expect(
			wrapper.get('[data-testid="select-Event"]').attributes('data-value')
		).toBe('New')
		expect(
			wrapper.get('[data-testid="select-Assign To"]').attributes('data-value')
		).toBe('member')
	})
})

describe('save is offered only for something to save', () => {
	it('disables Save on a badge nothing has been done to', async () => {
		const wrapper = await openBadge(mountPage())

		expect(
			wrapper.get('[data-testid="badge-save"]').attributes('disabled')
		).toBeDefined()
		expect(wrapper.find('[data-testid="badge-discard"]').exists()).toBe(false)
	})

	it('arms Save once a field changes, and still offers no Discard', async () => {
		const wrapper = await openBadge(mountPage())

		await field(wrapper, 'badge-title').setValue('Renamed')

		expect(
			wrapper.get('[data-testid="badge-save"]').attributes('disabled')
		).toBeUndefined()
		expect(wrapper.find('[data-testid="badge-discard"]').exists()).toBe(false)
	})

	it('disables Save on a new badge until something is typed', async () => {
		const wrapper = await openNew(mountPage())

		expect(
			wrapper.get('[data-testid="badge-save"]').attributes('disabled')
		).toBeDefined()

		await field(wrapper, 'badge-title').setValue('Champion II')

		expect(
			wrapper.get('[data-testid="badge-save"]').attributes('disabled')
		).toBeUndefined()
	})

	// Save is the only header action a form has, on an existing badge and on a
	// new one alike. Discarding is leaving: Back asks, and the unsaved badge in
	// the header is what says there is something to lose.
	it('offers Save and nothing else, dirty or not, new or not', async () => {
		for (const wrapper of [
			await openBadge(mountPage()),
			await openNew(mountPage()),
		]) {
			await field(wrapper, 'badge-title').setValue('Renamed')

			const actions = wrapper
				.findAll('[data-testid^="badge-"]')
				.map((node) => node.attributes('data-testid'))
				.filter((id) => id === 'badge-save' || id === 'badge-discard')

			expect(actions).toEqual(['badge-save'])
			expect(wrapper.text()).not.toContain('Discard')
		}
	})

	it('marks the header unsaved while there is an edit outstanding', async () => {
		const wrapper = await openBadge(mountPage())
		expect(wrapper.get('[data-unsaved]').attributes('data-unsaved')).toBe('no')

		await field(wrapper, 'badge-title').setValue('Renamed')

		expect(wrapper.get('[data-unsaved]').attributes('data-unsaved')).toBe('yes')
	})
})

describe('saving', () => {
	it('writes the record and goes back to the list', async () => {
		const wrapper = await openBadge(mountPage())

		await field(wrapper, 'badge-title').setValue('Renamed')
		await save(wrapper)
		await flushPromises()

		expect(saveMock).toHaveBeenCalled()
		expect(listReload).toHaveBeenCalled()
		expect(wrapper.find('[data-testid="list"]').exists()).toBe(true)
	})

	it('names the first missing field rather than sending an empty badge', async () => {
		const wrapper = await openNew(mountPage())

		await field(wrapper, 'badge-description').setValue('Won it')
		await save(wrapper)
		await flushPromises()

		expect(saveMock).not.toHaveBeenCalled()
		expect(wrapper.get('[data-testid="error"]').text()).toBe(
			'Title is required'
		)
	})
})
