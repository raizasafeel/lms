import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { reactive } from 'vue'
import type { CertificateDetails } from '@/utils/certificates'

const { resources, openExternalMock, copyMock } = vi.hoisted(() => ({
	resources: {} as Record<string, { data: unknown; error: unknown }>,
	openExternalMock: vi.fn(),
	copyMock: vi.fn(),
}))

vi.mock('@/stores/session', () => ({
	sessionStore: () => ({ brand: { name: 'Frappe School' } }),
}))
vi.mock('@/utils/openExternal', () => ({ openExternal: openExternalMock }))
vi.mock('@vueuse/core', async (importOriginal) => ({
	...(await importOriginal<typeof import('@vueuse/core')>()),
	useClipboard: () => ({ copy: copyMock }),
}))
vi.mock('frappe-ui', () => ({
	Avatar: {
		props: ['label'],
		template:
			'<span data-avatar>{{ label }}<span data-indicator v-if="$slots.indicator"><slot name="indicator" /></span></span>',
	},
	Tooltip: { props: ['text'], template: '<span><slot /></span>' },
	Badge: {
		props: ['label', 'theme'],
		template:
			'<span data-badge :data-theme="theme"><slot name="prefix" />{{ label }}<slot /></span>',
	},
	Button: {
		props: ['label', 'route'],
		emits: ['click'],
		template:
			'<button :data-route="route?.name" @click="$emit(\'click\')">{{ label }}<slot /></button>',
	},
	Dropdown: {
		props: ['options'],
		template:
			'<div data-dropdown><slot /><button v-for="o in options" :key="o.label" data-option @click="o.onClick()">{{ o.label }}</button></div>',
	},
	createResource: (options: { url: string }) => {
		const { data = null, error = null } = resources[options.url] ?? {}
		return reactive({ data, error, reload: () => {} })
	},
	createListResource: (options: { url: string }) =>
		reactive({
			data: resources[options.url]?.data ?? [],
			list: { loading: false },
			hasNextPage: false,
			pageLength: 24,
			update: () => {},
			reload: () => {},
		}),
	call: () => Promise.resolve(1063),
	FormControl: {
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template:
			'<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
	},
	usePageMeta: vi.fn(),
	toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/components/Layouts/pages/ListPage.vue', () => ({
	default: {
		props: ['rows'],
		template:
			'<div><slot name="toolbar" /><div v-for="row in rows" :key="row.key" data-card><slot name="card" :row="row" /></div></div>',
	},
}))
vi.mock('@/components/Layouts/pages/PageHeader.vue', () => ({
	default: {
		props: ['breadcrumbs'],
		template:
			'<header><span v-for="b in breadcrumbs" :key="b.label">{{ b.label }}</span></header>',
	},
}))

import CertificateVerification from '@/pages/CertificateVerification.vue'
// @ts-expect-error a JS SFC has no generated types (TS7016), as in profileUsernameKeys.test.ts.
import ProfileCertificates from '@/pages/ProfileCertificates.vue'
// @ts-expect-error a JS SFC has no generated types (TS7016).
import CertifiedParticipants from '@/pages/CertifiedParticipants.vue'

const certificate = (
	values: Partial<CertificateDetails> = {}
): CertificateDetails => ({
	name: '8f3k2q9a1c',
	kind: 'course',
	title: 'Frappe Framework',
	status: 'valid',
	issue_date: '2026-11-09',
	expiry_date: null,
	evaluator_name: 'Ana Ruiz',
	issued_by: 'Frappe School',
	is_member: false,
	member: {
		full_name: 'Maya Fernandes',
		username: 'maya',
		user_image: null,
		headline: 'Frappe developer at Globex',
	},
	awarded_for: {
		name: 'frappe-framework',
		title: 'Frappe Framework',
		category: 'Development',
		description: 'Build full-stack business apps.',
		image: null,
	},
	html: '<html></html>',
	...values,
})

const mountPage = (data: CertificateDetails | null, error: unknown = null) => {
	resources['lms.lms.api.get_certificate'] = { data, error }
	return mount(CertificateVerification, {
		props: { certificateId: '8f3k2q9a1c' },
		global: {
			mocks: { __ },
			stubs: { RouterLink: RouterLinkStub, CertificatePreview: true },
		},
	})
}

const details = (wrapper: ReturnType<typeof mountPage>) =>
	Object.fromEntries(
		wrapper
			.findAll('dl > div')
			.map((row) => [row.find('dt').text(), row.find('dd').text()])
	)

describe('CertificateVerification', () => {
	beforeEach(() => {
		openExternalMock.mockClear()
		copyMock.mockClear()
	})

	it('shows a valid certificate with its details', () => {
		const wrapper = mountPage(certificate())
		expect(wrapper.find('[data-badge]').text()).toBe('Verified')
		expect(wrapper.text()).toContain('Course certificate')
		expect(wrapper.find('h1').text()).toBe('Frappe Framework')
		expect(wrapper.text()).toContain(
			'Awarded to Maya Fernandes by Frappe School on 9 November 2026.'
		)
		expect(wrapper.text()).toContain('Valid certificate')
		expect(details(wrapper)).toEqual({
			'Certificate ID': '8f3k2q9a1c',
			'Awarded to': 'Maya Fernandes',
			'Issued on': '09 Nov 2026',
			'Valid till': 'No expiry',
			Evaluator: 'Ana Ruiz',
			'Issued by': 'Frappe School',
		})
		expect(wrapper.text()).toContain('About the course')
		expect(wrapper.text()).toContain('Evaluated by Ana Ruiz')
	})

	it('links the member card to their certificates', () => {
		const wrapper = mountPage(certificate())
		const links = wrapper.findAllComponents(RouterLinkStub)
		expect(links.map((link) => link.props('to'))).toContainEqual({
			name: 'ProfileCertificates',
			params: { username: 'maya' },
		})
	})

	it('downloads the PDF through the permission-checked endpoint', async () => {
		const wrapper = mountPage(certificate())
		const download = wrapper
			.findAll('button')
			.find((button) => button.text() === 'Download PDF')
		await download!.trigger('click')
		expect(openExternalMock).toHaveBeenCalledWith(
			'/api/method/lms.lms.api.download_certificate_pdf?certificate=8f3k2q9a1c'
		)
	})

	it('shares the short verification link', async () => {
		const wrapper = mountPage(certificate())
		const options = wrapper.findAll('[data-option]')
		await options.find((o) => o.text() === 'Copy link')!.trigger('click')
		expect(copyMock).toHaveBeenCalledWith(
			`${window.location.origin}/certificates/8f3k2q9a1c`
		)
		await options
			.find((o) => o.text() === 'Share on LinkedIn')!
			.trigger('click')
		expect(openExternalMock).toHaveBeenCalledWith(
			`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(
				`${window.location.origin}/certificates/8f3k2q9a1c`
			)}`
		)
	})

	it('marks an expired certificate', () => {
		const wrapper = mountPage(
			certificate({ status: 'expired', expiry_date: '2026-01-31' })
		)
		expect(wrapper.find('[data-badge]').text()).toBe('Expired')
		expect(wrapper.text()).toContain('Verified, but expired')
		expect(details(wrapper)['Expired on']).toBe('31 Jan 2026')
	})

	it('tells the member an unpublished certificate is theirs alone', () => {
		const wrapper = mountPage(
			certificate({ status: 'unpublished', is_member: true })
		)
		expect(wrapper.find('[data-badge]').text()).toBe('Not published')
		expect(wrapper.text()).toContain('Only you can see this')
		expect(wrapper.find('[data-dropdown]').exists()).toBe(false)
	})

	it('shows a batch certificate without a course card', () => {
		const wrapper = mountPage(
			certificate({ kind: 'batch', awarded_for: null, evaluator_name: null })
		)
		expect(wrapper.text()).toContain('Batch certificate')
		expect(wrapper.text()).not.toContain('About the')
		expect(details(wrapper)).not.toHaveProperty('Evaluator')
	})

	it('says when a certificate does not exist', () => {
		const wrapper = mountPage(null, { exc_type: 'DoesNotExistError' })
		expect(wrapper.text()).toContain('Certificate not found')
		expect(wrapper.text()).toContain(
			'No certificate on Frappe School has this ID'
		)
		expect(wrapper.text()).toContain('Browse courses')
	})

	it('says when a certificate is not published', () => {
		const wrapper = mountPage(null, { exc_type: 'PermissionError' })
		expect(wrapper.text()).toContain('Certificate unavailable')
	})
})

describe('ProfileCertificates', () => {
	const mountProfile = (rows: unknown[]) => {
		resources['lms.lms.api.get_user_certificates'] = { data: rows, error: null }
		return mount(ProfileCertificates, {
			props: { profile: { data: { username: 'farhan' } } },
			global: {
				mocks: { __ },
				stubs: { RouterLink: RouterLinkStub, CertificateThumbnail: true },
			},
		})
	}

	it('lists each certificate with a count, its kind and issue date', () => {
		const wrapper = mountProfile([
			{
				name: 'abc123',
				course: 'erpnext',
				course_title: 'ERPNext Essentials',
				issue_date: '2026-08-21',
				published: 1,
			},
		])
		expect(wrapper.find('h2').text()).toBe('Certificates')
		expect(wrapper.find('h2 + span').text()).toBe('1')
		expect(wrapper.text()).toContain('ERPNext Essentials')
		expect(wrapper.text()).toContain('Course · Issued 21 Aug 2026')
		expect(
			wrapper.find('[data-route="CertificateVerification"]').exists()
		).toBe(true)
		expect(wrapper.text()).not.toContain('Not published')
	})

	it('downloads and copies the link of a certificate', async () => {
		const wrapper = mountProfile([
			{
				name: 'abc123',
				batch_title: 'Spring cohort',
				issue_date: '2026-08-21',
				published: 1,
			},
		])
		expect(wrapper.text()).toContain('Batch · Issued 21 Aug 2026')
		const buttons = wrapper.findAll('button')
		await buttons.find((b) => b.text() === 'Download PDF')!.trigger('click')
		expect(openExternalMock).toHaveBeenCalledWith(
			'/api/method/lms.lms.api.download_certificate_pdf?certificate=abc123'
		)
		await buttons.find((b) => b.text() === 'Copy link')!.trigger('click')
		expect(copyMock).toHaveBeenCalledWith(
			`${window.location.origin}/certificates/abc123`
		)
	})

	it('marks an unpublished certificate and offers no link to copy', () => {
		const wrapper = mountProfile([
			{
				name: 'abc123',
				course: 'c',
				course_title: 'Data',
				issue_date: '2026-08-21',
				published: 0,
			},
		])
		expect(wrapper.text()).toContain('Not published')
		expect(
			wrapper.findAll('button').some((b) => b.text() === 'Copy link')
		).toBe(false)
	})
})

describe('CertifiedParticipants', () => {
	beforeEach(() => {
		window.history.replaceState({}, '', '/lms/certified-participants')
		delete resources['lms.lms.api.get_certification_categories']
		// jsdom has no layout, so no scrollIntoView.
		Element.prototype.scrollIntoView = vi.fn()
	})

	const member = (values: Record<string, unknown>) => ({
		full_name: 'Rashid Shaikh',
		username: 'rashid',
		headline: '',
		creation: '2026-07-25 10:00:00',
		open_to: '',
		certificates: [
			{ name: 'cert2', title: 'ERPNext' },
			{ name: 'cert1', title: 'Frappe Framework' },
		],
		...values,
	})

	const mountMembers = async (rows: unknown[]) => {
		resources['lms.lms.api.get_certified_participants'] = {
			data: rows,
			error: null,
		}
		const wrapper = mount(CertifiedParticipants, {
			global: {
				mocks: { __ },
				provide: { $user: { data: { name: 'me@example.com' } } },
				stubs: {
					RouterLink: RouterLinkStub,
					CertificateThumbnail: {
						props: ['certificate'],
						template: '<div data-thumbnail>{{ certificate }}</div>',
					},
					ClearableCombobox: true,
					ToggleFilter: true,
				},
			},
		})
		await flushPromises()
		return wrapper
	}

	it('counts the members under the filters', async () => {
		const wrapper = await mountMembers([member({})])
		expect(wrapper.find('[data-testid="member-count"]').text()).toBe(
			'1063 certified members'
		)
	})

	it('filters by category chip, with All selected by default', async () => {
		resources['lms.lms.api.get_certification_categories'] = {
			data: [{ label: 'ERPNext', value: 'ERPNext' }],
			error: null,
		}
		const wrapper = await mountMembers([member({})])
		const all = wrapper.find('[data-testid="category-All"]')
		const erpnext = wrapper.find('[data-testid="category-ERPNext"]')
		expect(all.attributes('aria-pressed')).toBe('true')
		await erpnext.trigger('click')
		await flushPromises()
		expect(erpnext.attributes('aria-pressed')).toBe('true')
		expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
		expect(all.attributes('aria-pressed')).toBe('false')
		expect(window.location.search).toContain('category=ERPNext')
		await all.trigger('click')
		expect(window.location.search).not.toContain('category')
	})

	it('never shows an empty category chip', async () => {
		resources['lms.lms.api.get_certification_categories'] = {
			data: [
				{ label: ' ', value: ' ' },
				{ label: '', value: '' },
				{ label: 'ERPNext', value: 'ERPNext' },
			],
			error: null,
		}
		const wrapper = await mountMembers([member({})])
		const chips = wrapper.findAll('[role="group"] button')
		expect(chips.map((chip) => chip.text())).toEqual(['All', 'ERPNext'])
	})

	it.each(['open-to-work', 'hiring'])(
		'toggles the %s filter as a pressed button',
		async (testid) => {
			const wrapper = await mountMembers([member({})])
			const toggle = wrapper.find(`[data-testid="${testid}"]`)
			expect(toggle.attributes('aria-pressed')).toBe('false')
			await toggle.trigger('click')
			expect(toggle.attributes('aria-pressed')).toBe('true')
			expect(window.location.search).toContain(`${testid}=true`)
			await toggle.trigger('click')
			expect(toggle.attributes('aria-pressed')).toBe('false')
		}
	)

	it('shows the member over their certificate stack and links to their profile', async () => {
		const wrapper = await mountMembers([
			member({ headline: 'Frappe developer' }),
		])
		const card = wrapper.find('[data-card]')
		expect(card.find('[data-thumbnail]').text()).toBe('cert2')
		expect(card.findAll('[data-sheet]')).toHaveLength(2)
		expect(card.text()).toContain('Rashid Shaikh')
		expect(card.text()).toContain('Frappe developer')
		expect(card.findComponent(RouterLinkStub).props('to')).toEqual({
			name: 'ProfileAbout',
			params: { username: 'rashid' },
		})
	})

	it.each([
		[
			'Enabling Digital Transformation for Enterprises 🟧',
			'Enabling Digital Transformation…',
		],
		['🚀 Frappe | Developer', 'Frappe Developer'],
		['ERPNext Consultant', 'ERPNext Consultant'],
	])('shortens the headline "%s" to three words', async (headline, shown) => {
		const wrapper = await mountMembers([member({ headline })])
		const line = wrapper
			.findAll('[data-card] div')
			.find((div) => div.attributes('title') === headline)
		expect(line?.text()).toBe(shown)
	})

	it('says when a member without a headline joined', async () => {
		const wrapper = await mountMembers([member({})])
		expect(wrapper.find('[data-card]').text()).toMatch(/Joined .+ ago/)
	})

	it.each([
		['Work', 'Open to Work'],
		['Hiring', 'Hiring'],
	])(
		'marks a member open to %s with a dot on the avatar',
		async (openTo, label) => {
			const wrapper = await mountMembers([member({ open_to: openTo })])
			expect(
				wrapper
					.find('[data-card] [data-indicator] [role="img"]')
					.attributes('aria-label')
			).toBe(label)
		}
	)

	it('shows no status dot without an open_to value', async () => {
		const wrapper = await mountMembers([member({})])
		expect(wrapper.find('[data-card] [data-indicator]').exists()).toBe(false)
	})

	it('plays the stack while the card is hovered or focused', async () => {
		const wrapper = await mountMembers([member({})])
		const card = wrapper.find('[data-card] > *')
		const stack = wrapper.findComponent({ name: 'CertificateStack' })
		await card.trigger('pointerenter')
		expect(stack.props('playing')).toBe(true)
		await card.trigger('pointerleave')
		expect(stack.props('playing')).toBe(false)
		await card.trigger('focusin')
		expect(stack.props('playing')).toBe(true)
		await card.trigger('focusout')
		expect(stack.props('playing')).toBe(false)
	})
})
