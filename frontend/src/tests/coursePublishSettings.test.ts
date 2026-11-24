import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import CoursePublishSettings from '@/pages/Courses/CoursePublishSettings.vue'

vi.hoisted(() => {
	// @/utils pulls in plyr, which touches matchMedia at import time.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

vi.mock('@/stores/settings', () => ({
	useSettings: () => ({
		settings: { data: { is_payments_app_installed: 1 } },
	}),
}))

vi.mock('frappe-ui', () => ({
	Button: { template: '<button v-bind="$attrs"><slot /></button>' },
	Dialog: { template: '<div><slot /></div>' },
	FormControl: { template: '<div />' },
	createResource: ({ url }: { url: string }) => ({
		data:
			url === 'lms.lms.api.get_certificate_designs'
				? {
						designs: ['Certificate', 'Certificate Modern'],
						default: 'Certificate',
				  }
				: null,
		reload: vi.fn(),
		submit: vi.fn(),
	}),
}))

vi.mock('@framework/ui/telemetry/index', () => ({}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({}))

// The People groups have their own tests; here they only hand on their slots.
const PeopleGroup = {
	name: 'PeopleGroup',
	props: ['modelValue', 'owner', 'canChangeOwner'],
	template: '<div />',
}
const EvaluationGroup = {
	name: 'EvaluationGroup',
	props: ['enabled', 'people', 'format', 'duration'],
	emits: ['update:enabled'],
	template: '<div><slot /><slot name="certificate" /></div>',
}
const groups = { PeopleGroup, EvaluationGroup }

const formFor = (courseDoc: Record<string, unknown>, markDirty = vi.fn()) => ({
	resource: { doc: courseDoc },
	people: ref([{ member: 'eve@example.com', role: 'Grader' }]),
	markDirty,
})
const $user = { data: { name: 'ash@example.com', is_moderator: false } }

vi.stubGlobal('__', (s: string) => s)

const doc = {
	name: 'COURSE-1',
	upcoming: 0,
	featured: 0,
	disable_self_learning: 0,
	enforce_lesson_completion: 0,
}

describe('CoursePublishSettings', () => {
	it('marks the form dirty when the switch is flipped', async () => {
		const markDirty = vi.fn()
		const wrapper = mount(CoursePublishSettings, {
			global: {
				mocks: { __: (s: string) => s },
				provide: {
					courseForm: formFor({ ...doc }, markDirty),
					$user,
					$dayjs: (v: unknown) => ({ format: () => String(v) }),
				},
				stubs: {
					...groups,
					CollapsibleSection: { template: '<div><slot /></div>' },
					Link: true,
					BooleanSwitch: {
						props: ['modelValue', 'label'],
						emits: ['update:modelValue'],
						template: `<button
							:data-label="label"
							@click="$emit('update:modelValue', !modelValue)"
						/>`,
					},
				},
			},
		})

		await wrapper.find('[data-label="Lessons in sequence"]').trigger('click')
		expect(markDirty).toHaveBeenCalled()
	})
})

describe('CoursePublishSettings certificate design', () => {
	function mountWithCertification(extra: Record<string, unknown> = {}) {
		const markDirty = vi.fn()
		const courseDoc: Record<string, unknown> = {
			...doc,
			title: 'Data',
			enable_certification: 1,
			...extra,
		}
		const wrapper = mount(CoursePublishSettings, {
			global: {
				mocks: { __: (s: string) => s },
				provide: {
					courseForm: formFor(courseDoc, markDirty),
					$user,
					$dayjs: (v: unknown) => ({ format: () => String(v) }),
				},
				stubs: {
					...groups,
					CollapsibleSection: { template: '<div><slot /></div>' },
					Link: true,
					BooleanSwitch: true,
					CertificateDesignDialog: {
						name: 'CertificateDesignDialog',
						props: ['open', 'current'],
						emits: ['select', 'update:open'],
						template: '<div />',
					},
				},
			},
		})
		return { wrapper, markDirty, courseDoc }
	}

	it('names the site default when the course has no design', () => {
		const { wrapper } = mountWithCertification()
		expect(wrapper.text()).toContain('Original')
	})

	it('names the course design when one is set', () => {
		const { wrapper } = mountWithCertification({
			certificate_template: 'Certificate Modern',
		})
		expect(wrapper.text()).toContain('Modern')
	})

	it('stores the chosen design on the course and marks the form dirty', async () => {
		const { wrapper, markDirty, courseDoc } = mountWithCertification()
		await wrapper.find('button').trigger('click')
		const dialog = wrapper.findComponent({ name: 'CertificateDesignDialog' })
		expect(dialog.props('open')).toBe(true)
		dialog.vm.$emit('select', 'Certificate Modern')
		expect(courseDoc.certificate_template).toBe('Certificate Modern')
		expect(markDirty).toHaveBeenCalled()
	})

	it('hides the row when the course offers no certificate', () => {
		const { wrapper } = mountWithCertification({ enable_certification: 0 })
		expect(wrapper.text()).not.toContain('Certificate design')
	})
})

describe('CoursePublishSettings evaluation', () => {
	const mountWith = (extra: Record<string, unknown>, user = $user) => {
		const courseDoc: Record<string, unknown> = {
			...doc,
			owner: 'ash@example.com',
			...extra,
		}
		const markDirty = vi.fn()
		const wrapper = mount(CoursePublishSettings, {
			global: {
				mocks: { __: (s: string) => s },
				provide: { courseForm: formFor(courseDoc, markDirty), $user: user },
				stubs: {
					...groups,
					BooleanSwitch: true,
					CertificateDesignDialog: true,
				},
			},
		})
		return { wrapper, courseDoc, markDirty }
	}

	it('turns evaluations on as the paid certificate, off the automatic one', async () => {
		const { wrapper, courseDoc, markDirty } = mountWith({
			enable_certification: 1,
		})
		const group = wrapper.findComponent({ name: 'EvaluationGroup' })
		expect(group.props('enabled')).toBe(false)
		group.vm.$emit('update:enabled', true)
		expect(courseDoc.paid_certificate).toBe(1)
		expect(courseDoc.enable_certification).toBe(0)
		expect(markDirty).toHaveBeenCalled()
	})

	it('hands the Grader rows to both People and the evaluators list', () => {
		const { wrapper } = mountWith({ paid_certificate: 1 })
		const rows = [{ member: 'eve@example.com', role: 'Grader' }]
		expect(
			wrapper.findComponent({ name: 'PeopleGroup' }).props('modelValue')
		).toEqual(rows)
		expect(
			wrapper.findComponent({ name: 'EvaluationGroup' }).props('people')
		).toEqual(rows)
	})

	it('lets only the owner or a Moderator change the owner', () => {
		const canChange = (user: typeof $user) =>
			mountWith({}, user)
				.wrapper.findComponent({ name: 'PeopleGroup' })
				.props('canChangeOwner')
		expect(canChange($user)).toBe(true)
		expect(
			canChange({ data: { name: 'bo@example.com', is_moderator: false } })
		).toBe(false)
		expect(
			canChange({ data: { name: 'bo@example.com', is_moderator: true } })
		).toBe(true)
	})
})
