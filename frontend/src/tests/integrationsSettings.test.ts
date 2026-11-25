/**
 * Settings > Integrations: the grid of cards, what each card offers in each
 * state, which integration pages the sidebar lists, and the pages Configure
 * opens. Only the server, the settings documents, toasts and navigation are
 * replaced; the cards, switches, inputs and buttons are the shipped ones.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'

vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

const server = vi.hoisted(() => ({
	status: null as unknown,
	refuse: false,
	calls: [] as { url: string; params?: unknown }[],
}))
const navigation = vi.hoisted(() => ({ slugs: [] as string[] }))
const external = vi.hoisted(() => ({ urls: [] as string[] }))
const flowPanel = vi.hoisted(() => ({ open: false }))
const failures = vi.hoisted(() => ({ reported: [] as unknown[] }))
const sources = vi.hoisted(
	() =>
		[] as {
			doc: Record<string, unknown>
			isDirty: boolean
			save: () => Promise<unknown>
			reload: () => Promise<unknown>
		}[]
)
const guards = vi.hoisted(
	() => [] as { isDirty: () => boolean; discard?: () => void }[]
)

vi.mock('frappe-ui', async () => {
	const actual = (await vi.importActual('frappe-ui')) as Record<string, unknown>
	return new Proxy(actual, {
		get(target, key: string) {
			if (key === 'call')
				return (url: string, params?: unknown) => {
					server.calls.push({ url, params })
					if (server.refuse && url.endsWith('set_integrations_enabled'))
						return Promise.reject({ messages: ['Refused'] })
					return Promise.resolve(server.status)
				}
			if (key === 'toast') return { error: () => {}, success: () => {} }
			return (target as Record<string, unknown>)[key]
		},
	})
})
vi.mock('@/utils', () => ({
	openSettings: (slug: string) => navigation.slugs.push(slug),
}))
vi.mock('@/utils/openExternal', () => ({
	openExternal: (url: string) => external.urls.push(url),
}))
vi.mock('@/composables/useDirtyGuard', () => ({
	useDirtyGuard: (isDirty: () => boolean, discard?: () => void) =>
		guards.push({ isDirty, discard }),
}))
vi.mock('@/composables/useSettingsSource', async (importOriginal) => ({
	...((await importOriginal()) as object),
	reportSaveFailure: (error: unknown) => failures.reported.push(error),
	useSettingsSource: () => {
		const source = reactive({
			doc: {} as Record<string, unknown>,
			isDirty: false,
			save: vi.fn(() => Promise.resolve()),
			reload: vi.fn(() => Promise.resolve()),
		})
		sources.push(source)
		return source
	},
}))
vi.mock('@/composables/useFlowDocked', async () => {
	const { computed } = await import('vue')
	return { useFlowDocked: () => computed(() => flowPanel.open) }
})
vi.mock('@framework/ui/telemetry/index', () => ({}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({}))
vi.mock('@/stores/user', () => ({
	usersStore: () => ({
		userResource: { data: { is_moderator: true, is_system_manager: true } },
	}),
}))

const __t = (text: string, args?: unknown[]): string =>
	args
		? text.replace(/\{(\d+)\}/g, (_m, i) => String(args[Number(i)] ?? ''))
		: text
vi.stubGlobal('__', __t)
;(String.prototype as unknown as { format?: unknown }).format ??= function (
	...args: string[]
) {
	return args.reduce((out, arg, i) => out.replace(`{${i}}`, arg), String(this))
}
const mountOptions = { global: { mocks: { __: __t } } }

import Integrations from '@/components/Settings/Integrations/Integrations.vue'
import GoogleConfig from '@/components/Settings/Integrations/GoogleConfig.vue'
import UnsplashConfig from '@/components/Settings/Integrations/UnsplashConfig.vue'
import FlowConfig from '@/components/Settings/Integrations/FlowConfig.vue'
import ZoomConfig from '@/components/Settings/Integrations/ZoomConfig.vue'
import {
	integrationStatus,
	isSidebarItemVisible,
	type IntegrationStatus,
} from '@/components/Settings/Integrations/integrations'
import { settingsTree } from '@/components/Settings/settings'

const STATUS_URL = 'lms.lms.integrations.get_integration_status'
const SAVE_URL = 'lms.lms.integrations.set_integrations_enabled'

const baseStatus = (): IntegrationStatus => ({
	google: { enabled: true, has_credentials: false, permitted: true },
	google_calendar: { enabled: true, calendars: 5, need_access: 1 },
	google_meet: { enabled: true, accounts: 1 },
	zoom: { enabled: false, attendance: true, accounts: 2 },
	code_runner: { enabled: true, own_server: true },
	unsplash: { enabled: false, has_key: false },
	raven: { enabled: false, raven: true, raven_integration: false },
	flow: {
		installed: true,
		enabled: true,
		hide_for_learners: true,
		ready: true,
	},
})

const withZoom = (enabled: boolean): IntegrationStatus => ({
	...baseStatus(),
	zoom: { ...baseStatus().zoom, enabled },
})

const card = (wrapper: ReturnType<typeof mount>, key: string) =>
	wrapper.get(`[data-testid="integration-${key}"]`)

const configure = (wrapper: ReturnType<typeof mount>, key: string) =>
	card(wrapper, key).get('[data-testid="integration-configure"]')

const records = (wrapper: ReturnType<typeof mount>, key: string) =>
	card(wrapper, key).get('[data-testid="integration-records"]')

const buttons = (wrapper: ReturnType<typeof mount>, key: string) =>
	card(wrapper, key)
		.findAll('button:not([role="switch"])')
		.map((button) => button.text())

const mountGrid = async (record: string | null = null) => {
	const wrapper = mount(Integrations, { ...mountOptions, props: { record } })
	await flushPromises()
	return wrapper
}

beforeEach(() => {
	server.status = baseStatus()
	server.refuse = false
	server.calls = []
	navigation.slugs = []
	external.urls = []
	failures.reported = []
	sources.length = 0
	guards.length = 0
	flowPanel.open = false
	integrationStatus.value = null
})

describe('the Integrations grid', () => {
	it('draws a card for every integration the LMS supports', async () => {
		const wrapper = await mountGrid()
		expect(server.calls[0].url).toBe(STATUS_URL)
		const keys = wrapper
			.findAll('[data-enabled]')
			.map((node) => node.attributes('data-testid'))
		expect(keys).toEqual([
			'integration-google',
			'integration-google_calendar',
			'integration-google_meet',
			'integration-zoom',
			'integration-code_runner',
			'integration-unsplash',
			'integration-raven',
			'integration-flow',
		])
	})

	it('reports each card in its own words, warnings in a readable ink', async () => {
		const wrapper = await mountGrid()
		const line = (key: string) =>
			card(wrapper, key).get('[data-testid="integration-status"]')
		expect(line('google').text()).toBe('Needs a client ID and secret')
		expect(line('google').classes()).toContain('text-ink-amber-8')
		expect(line('google_calendar').text()).toBe('5 calendars · 1 need access')
		expect(line('google_meet').text()).toBe('1 account')
		expect(line('code_runner').text()).toBe('Your own server')
		expect(line('zoom').text()).toBe('Off')
		expect(line('raven').text()).toBe('Needs the Raven integration app')
		expect(line('flow').text()).toBe('Connected · hidden for learners')
	})

	it('has no Save: a switch saves the moment it flips', async () => {
		const wrapper = await mountGrid()
		expect(wrapper.find('[data-testid="integrations-save"]').exists()).toBe(
			false
		)
		server.status = withZoom(true)
		await card(wrapper, 'zoom').get('[role="switch"]').trigger('click')
		await flushPromises()
		expect(server.calls[1]).toEqual({
			url: SAVE_URL,
			params: { changes: { zoom: true } },
		})
		expect(card(wrapper, 'zoom').attributes('data-enabled')).toBe('true')
		expect(
			card(wrapper, 'zoom').get('[data-testid="integration-status"]').text()
		).toBe('2 accounts · attendance on')
	})

	it('puts a refused switch back and says why', async () => {
		const wrapper = await mountGrid()
		server.refuse = true
		await card(wrapper, 'zoom').get('[role="switch"]').trigger('click')
		await flushPromises()
		expect(failures.reported).toEqual([{ messages: ['Refused'] }])
		expect(card(wrapper, 'zoom').attributes('data-enabled')).toBe('false')
	})

	it('mutes an off card and keeps its page closed', async () => {
		const wrapper = await mountGrid()
		expect(card(wrapper, 'zoom').classes()).toContain('bg-surface-gray-1')
		expect(configure(wrapper, 'zoom').attributes()).toHaveProperty('disabled')
		expect(records(wrapper, 'zoom').attributes()).toHaveProperty('disabled')
	})

	it('splits Configure from the list of records on each card', async () => {
		server.status = {
			...withZoom(true),
			raven: { enabled: true, raven: true, raven_integration: true },
		}
		const wrapper = await mountGrid()
		expect(buttons(wrapper, 'google')).toEqual(['Configure'])
		expect(buttons(wrapper, 'google_calendar')).toEqual(['Calendars'])
		expect(buttons(wrapper, 'google_meet')).toEqual(['Accounts'])
		expect(buttons(wrapper, 'zoom')).toEqual(['Configure', 'Accounts'])
		expect(buttons(wrapper, 'code_runner')).toEqual(['Configure'])
		expect(buttons(wrapper, 'unsplash')).toEqual(['Configure'])
		expect(buttons(wrapper, 'raven')).toEqual(['Workspaces'])
		expect(buttons(wrapper, 'flow')).toEqual(['Configure'])
	})

	it('opens a simple integration in place, on or off, and comes back', async () => {
		const wrapper = await mountGrid()
		await configure(wrapper, 'google').trigger('click')
		await configure(wrapper, 'unsplash').trigger('click')
		expect(wrapper.emitted('update:record')).toEqual([['google'], ['unsplash']])
		expect(navigation.slugs).toEqual([])

		const page = await mountGrid('unsplash')
		expect(page.find('[data-enabled]').exists()).toBe(false)
		expect(page.find('[data-testid="integration-intro"]').exists()).toBe(true)
		await page.get('header button').trigger('click')
		expect(page.emitted('update:record')).toEqual([[null]])
	})

	it('opens Zoom’s settings in place and its accounts in the sidebar', async () => {
		server.status = withZoom(true)
		const wrapper = await mountGrid()
		await configure(wrapper, 'zoom').trigger('click')
		await records(wrapper, 'zoom').trigger('click')
		expect(wrapper.emitted('update:record')).toEqual([['zoom']])
		expect(navigation.slugs).toEqual(['zoom'])
	})

	it('sends Calendar and Meet to their own sidebar pages', async () => {
		const wrapper = await mountGrid()
		await records(wrapper, 'google_calendar').trigger('click')
		await records(wrapper, 'google_meet').trigger('click')
		expect(navigation.slugs).toEqual(['google-calendar', 'google-meet'])
	})

	it('keeps Calendar’s list shut while Calendar is off', async () => {
		server.status = {
			...baseStatus(),
			google_calendar: { enabled: false, calendars: 0, need_access: 0 },
		}
		const wrapper = await mountGrid()
		expect(records(wrapper, 'google_calendar').attributes()).toHaveProperty(
			'disabled'
		)
	})

	it('offers to install Raven’s apps in place of its switch and list', async () => {
		const wrapper = await mountGrid()
		const raven = card(wrapper, 'raven')
		expect(raven.find('[role="switch"]').exists()).toBe(false)
		expect(raven.find('[data-testid="integration-records"]').exists()).toBe(
			false
		)
		const install = raven.get('[data-testid="integration-install"]')
		expect(install.text()).toContain('Install required apps')
		await install.trigger('click')
		expect(external.urls).toEqual([
			'https://github.com/raizasafeel/raven_integration',
		])
	})

	it('shows Raven’s switch and workspaces once its apps are installed', async () => {
		server.status = {
			...baseStatus(),
			raven: { enabled: true, raven: true, raven_integration: true },
		}
		const wrapper = await mountGrid()
		const raven = card(wrapper, 'raven')
		expect(raven.find('[role="switch"]').exists()).toBe(true)
		await raven.get('[data-testid="integration-records"]').trigger('click')
		expect(navigation.slugs).toEqual(['raven'])
	})

	it('locks Calendar and Meet until Google has its credentials', async () => {
		server.status = {
			...baseStatus(),
			google_calendar: { enabled: false, calendars: 0, need_access: 0 },
			google_meet: { enabled: false, accounts: 0 },
		}
		const locked = await mountGrid()
		for (const key of ['google_calendar', 'google_meet'])
			expect(
				card(locked, key).get('[role="switch"]').attributes()
			).toHaveProperty('disabled')

		server.status = {
			...(server.status as IntegrationStatus),
			google: { enabled: true, has_credentials: true, permitted: true },
		}
		const ready = await mountGrid()
		expect(
			card(ready, 'google_meet').get('[role="switch"]').attributes()
		).not.toHaveProperty('disabled')
	})
})

describe('the settings sidebar', () => {
	const sidebarSlugs = () =>
		settingsTree
			.find((group) => group.label === 'Integrations')!
			.items.filter(isSidebarItemVisible)
			.map((item) => item.slug)

	it('lists the grid and only the integrations that are on', () => {
		integrationStatus.value = baseStatus()
		expect(sidebarSlugs()).toEqual([
			'integrations',
			'google-calendar',
			'google-meet',
		])
	})

	it('adds an integration once it is turned on', () => {
		integrationStatus.value = withZoom(true)
		expect(sidebarSlugs()).toContain('zoom')
	})

	it('lists no integration page before the status has loaded', () => {
		expect(sidebarSlugs()).toEqual(['integrations'])
	})

	it('keeps simple integrations out of the sidebar, and Services gone', () => {
		const slugs = settingsTree.flatMap((g) => g.items.map((i) => i.slug))
		for (const slug of [
			'services',
			'google',
			'code-runner',
			'unsplash',
			'flow',
		])
			expect(slugs).not.toContain(slug)
	})
})

describe('an integration page', () => {
	it('opens with the integration’s icon and purpose', () => {
		const wrapper = mount(UnsplashConfig, mountOptions)
		expect(wrapper.get('[data-testid="integration-intro"]').text()).toBe(
			'Lets people pick cover images from Unsplash.'
		)
		expect(wrapper.get('header').text()).toContain('Unsplash')
	})

	it('saves its own fields on its own Save', async () => {
		const wrapper = mount(UnsplashConfig, mountOptions)
		const [lms] = sources
		const save = wrapper.get('[data-testid="unsplash-save"]')
		expect(save.attributes()).toHaveProperty('disabled')

		const key = wrapper.get('input[type="password"]')
		expect(key.attributes('placeholder')).toBe('Paste your Unsplash access key')
		await key.setValue('abc')
		expect(lms.doc.unsplash_access_key).toBe('abc')

		lms.isDirty = true
		await wrapper.vm.$nextTick()
		await save.trigger('click')
		await flushPromises()
		expect(lms.save).toHaveBeenCalledOnce()
		expect(server.calls.map((call) => call.url)).toEqual([STATUS_URL])
	})

	it('guards a typed Google client secret and clears it on discard', async () => {
		const wrapper = mount(GoogleConfig, mountOptions)
		const guard = guards.at(-1)!
		expect(guard.isDirty()).toBe(false)

		const secret = wrapper.get('input[type="password"]')
		await secret.setValue('s3cret')
		expect(guard.isDirty()).toBe(true)

		guard.discard?.()
		await wrapper.vm.$nextTick()
		expect(guard.isDirty()).toBe(false)
		expect((secret.element as HTMLInputElement).value).toBe('')
	})

	it('writes a Google client secret after the rest of Google Settings', async () => {
		const wrapper = mount(GoogleConfig, mountOptions)
		const [google] = sources
		google.isDirty = true
		await wrapper.get('input[type="password"]').setValue('s3cret')
		await wrapper.get('[data-testid="google-save"]').trigger('click')
		await flushPromises()
		expect(google.save).toHaveBeenCalledOnce()
		expect(server.calls[0]).toEqual({
			url: 'frappe.client.set_value',
			params: {
				doctype: 'Google Settings',
				name: 'Google Settings',
				fieldname: 'client_secret',
				value: 's3cret',
			},
		})
	})

	it('lets Flow be hidden from learners', async () => {
		integrationStatus.value = baseStatus()
		const wrapper = mount(FlowConfig, mountOptions)
		const [lms] = sources
		expect(wrapper.get('[data-testid="flow-connection"]').text()).toContain(
			'Connected'
		)
		await wrapper.get('[role="switch"]').trigger('click')
		expect(lms.doc.hide_flow_for_learners).toBe(1)
	})

	it('offers to open Flow only while its panel is closed', () => {
		integrationStatus.value = baseStatus()
		const closed = mount(FlowConfig, mountOptions)
		expect(closed.text()).toContain('Open Flow')
		flowPanel.open = true
		const open = mount(FlowConfig, mountOptions)
		expect(open.text()).not.toContain('Open Flow')
	})
})

describe('the Zoom page', () => {
	it('saves attendance tracking on its own Save', async () => {
		const wrapper = mount(ZoomConfig, mountOptions)
		const [lms] = sources
		expect(wrapper.get('header').text()).toContain('Zoom')
		await wrapper.get('[data-testid="zoom-attendance"]').trigger('click')
		expect(lms.doc.track_zoom_attendance).toBe(1)

		lms.isDirty = true
		await wrapper.vm.$nextTick()
		await wrapper.get('[data-testid="zoom-save"]').trigger('click')
		await flushPromises()
		expect(lms.save).toHaveBeenCalledOnce()
		expect(server.calls.map((call) => call.url)).toEqual([STATUS_URL])
	})

	it('opens from the grid in place of the cards', async () => {
		const page = await mountGrid('zoom')
		expect(page.find('[data-enabled]').exists()).toBe(false)
		expect(page.find('[data-testid="zoom-attendance"]').exists()).toBe(true)
	})
})
