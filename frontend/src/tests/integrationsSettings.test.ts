/**
 * Settings > Integrations: the grid of cards, what each card offers in each
 * state, the breadcrumb a configured page opens under, and which integration
 * pages the sidebar lists. Only the server call, toasts and navigation are
 * replaced; the cards, switches and buttons are the shipped ones.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

const server = vi.hoisted(() => ({
	status: null as unknown,
	calls: [] as { url: string; params?: unknown }[],
}))
const navigation = vi.hoisted(() => ({ slugs: [] as string[] }))
const external = vi.hoisted(() => ({ urls: [] as string[] }))

vi.mock('frappe-ui', async () => {
	const actual = (await vi.importActual('frappe-ui')) as Record<string, unknown>
	return new Proxy(actual, {
		get(target, key: string) {
			if (key === 'call')
				return (
					url: string,
					params?: { changes?: Record<string, boolean> }
				) => {
					server.calls.push({ url, params })
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
vi.mock('@/composables/useDirtyGuard', () => ({ useDirtyGuard: () => {} }))
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
import ZoomAttendanceSwitch from '@/components/Settings/Zoom/ZoomAttendanceSwitch.vue'
import SettingsCrumbScope from '@/components/Layouts/settings/desktop/SettingsCrumbScope.vue'
import SettingsHeader from '@/components/Layouts/settings/desktop/SettingsHeader.vue'
import {
	integrationStatus,
	isSidebarItemVisible,
	type IntegrationStatus,
} from '@/components/Settings/Integrations/integrations'
import { settingsTree } from '@/components/Settings/settings'

const STATUS_URL = 'lms.lms.integrations.get_integration_status'
const SAVE_URL = 'lms.lms.integrations.set_integrations_enabled'

const baseStatus = (): IntegrationStatus => ({
	google: { enabled: true, has_credentials: true, permitted: true },
	google_calendar: { enabled: true, calendars: 5, need_access: 1 },
	google_meet: { enabled: true, accounts: 1 },
	zoom: { enabled: false, attendance: true, accounts: 2 },
	code_runner: { enabled: true, own_server: true },
	unsplash: { enabled: false, has_key: false },
	raven: { enabled: false, raven: true, raven_integration: false },
	frappe_meet: { installed: false },
})

const card = (wrapper: ReturnType<typeof mount>, key: string) =>
	wrapper.get(`[data-testid="integration-${key}"]`)

const mountGrid = async () => {
	const wrapper = mount(Integrations, mountOptions)
	await flushPromises()
	return wrapper
}

beforeEach(() => {
	server.status = baseStatus()
	server.calls = []
	navigation.slugs = []
	external.urls = []
	integrationStatus.value = null
})

describe('the Integrations grid', () => {
	it('loads the status and draws a card for every integration', async () => {
		const wrapper = await mountGrid()
		expect(server.calls[0].url).toBe(STATUS_URL)
		const keys = wrapper
			.findAll('[data-testid^="integration-"][data-enabled]')
			.map((node) => node.attributes('data-testid'))
		expect(keys).toEqual([
			'integration-google',
			'integration-google_calendar',
			'integration-google_meet',
			'integration-zoom',
			'integration-code_runner',
			'integration-unsplash',
			'integration-raven',
			'integration-frappe_meet',
		])
	})

	it('reports each card in its own words', async () => {
		const wrapper = await mountGrid()
		const line = (key: string) =>
			card(wrapper, key).get('[data-testid="integration-status"]')
		expect(line('google').text()).toBe('Connected')
		expect(line('google_calendar').text()).toBe('5 calendars · 1 need access')
		expect(line('google_calendar').classes()).toContain('text-ink-amber-3')
		expect(line('google_meet').text()).toBe('1 account')
		expect(line('code_runner').text()).toBe('Your own server')
		expect(line('zoom').text()).toBe('Off')
		expect(line('raven').text()).toBe('Needs the Raven integration app')
		expect(line('frappe_meet').text()).toBe('Needs the Frappe Meet app')
	})

	it('mutes an off card and keeps it from being configured', async () => {
		const wrapper = await mountGrid()
		const zoom = card(wrapper, 'zoom')
		expect(zoom.attributes('data-enabled')).toBe('false')
		expect(zoom.classes()).toContain('bg-surface-gray-1')
		expect(
			zoom.get('[data-testid="integration-configure"]').attributes()
		).toHaveProperty('disabled')
	})

	it('offers Install instead of a switch when an app is missing', async () => {
		const wrapper = await mountGrid()
		const meet = card(wrapper, 'frappe_meet')
		expect(meet.find('[role="switch"]').exists()).toBe(false)
		expect(
			meet.get('[data-testid="integration-configure"]').attributes()
		).toHaveProperty('disabled')
		await meet.get('[data-testid="integration-install"]').trigger('click')
		expect(external.urls).toEqual([
			'https://cloud.frappe.io/marketplace/apps/meet',
		])
		expect(card(wrapper, 'zoom').find('[role="switch"]').exists()).toBe(true)
	})

	it('saves a toggle only on Save', async () => {
		const wrapper = await mountGrid()
		const save = wrapper.get('[data-testid="integrations-save"]')
		expect(save.attributes()).toHaveProperty('disabled')

		await card(wrapper, 'zoom').get('[role="switch"]').trigger('click')
		expect(card(wrapper, 'zoom').attributes('data-enabled')).toBe('true')
		expect(server.calls.map((call) => call.url)).toEqual([STATUS_URL])
		expect(save.attributes()).not.toHaveProperty('disabled')

		server.status = {
			...baseStatus(),
			zoom: { ...baseStatus().zoom, enabled: true },
		}
		await save.trigger('click')
		await flushPromises()
		expect(server.calls[1]).toEqual({
			url: SAVE_URL,
			params: { changes: { zoom: true } },
		})
		expect(save.attributes()).toHaveProperty('disabled')
		expect(
			card(wrapper, 'zoom').get('[data-testid="integration-status"]').text()
		).toBe('2 accounts · attendance on')
	})

	it('drops a toggle flipped back before saving', async () => {
		const wrapper = await mountGrid()
		const zoomSwitch = card(wrapper, 'zoom').get('[role="switch"]')
		await zoomSwitch.trigger('click')
		await zoomSwitch.trigger('click')
		expect(
			wrapper.get('[data-testid="integrations-save"]').attributes()
		).toHaveProperty('disabled')
	})

	it('opens an on integration’s page from Configure', async () => {
		const wrapper = await mountGrid()
		await card(wrapper, 'google_calendar')
			.get('[data-testid="integration-configure"]')
			.trigger('click')
		expect(navigation.slugs).toEqual(['google-calendar'])
	})

	it('locks the Google Meet switch while Google is off', async () => {
		server.status = {
			...baseStatus(),
			google: { enabled: false, has_credentials: false, permitted: true },
			google_meet: { enabled: false, accounts: 0 },
		}
		const wrapper = await mountGrid()
		expect(
			card(wrapper, 'google_meet').get('[role="switch"]').attributes()
		).toHaveProperty('disabled')
	})
})

describe('the integration breadcrumb', () => {
	const Page = defineComponent({
		props: { crumb: { type: Object, default: null } },
		setup: (props) => () =>
			h(SettingsCrumbScope, { crumb: props.crumb }, () =>
				h(SettingsHeader, { title: 'Zoom' })
			),
	})

	it('draws "← Integrations / Zoom" and goes back on click', async () => {
		const open = vi.fn()
		const wrapper = mount(Page, {
			...mountOptions,
			props: { crumb: { label: 'Integrations', open } },
		})
		const crumb = wrapper.get('[data-testid="settings-crumb"]')
		expect(crumb.text()).toContain('Integrations')
		expect(crumb.get('h2').text()).toBe('Zoom')
		await crumb
			.get('button[aria-label="Back to Integrations"]')
			.trigger('click')
		expect(open).toHaveBeenCalledOnce()
	})

	it('keeps the plain title on a page outside Integrations', () => {
		const wrapper = mount(Page, mountOptions)
		expect(wrapper.find('[data-testid="settings-crumb"]').exists()).toBe(false)
		expect(wrapper.get('h2').text()).toBe('Zoom')
	})
})

describe('the settings sidebar', () => {
	const sidebarSlugs = () =>
		settingsTree
			.find((group) => group.label === 'Integrations')!
			.items.filter(isSidebarItemVisible)
			.map((item) => item.slug)

	it('lists only the integrations that are on, plus the grid', () => {
		integrationStatus.value = baseStatus()
		expect(sidebarSlugs()).toEqual([
			'integrations',
			'services',
			'google-calendar',
			'google-meet',
		])
	})

	it('adds an integration once it is turned on', () => {
		integrationStatus.value = {
			...baseStatus(),
			zoom: { ...baseStatus().zoom, enabled: true },
		}
		expect(sidebarSlugs()).toContain('zoom')
	})

	it('lists no integration page before the status has loaded', () => {
		expect(sidebarSlugs()).toEqual(['integrations'])
	})
})

describe('the Zoom attendance switch', () => {
	it('writes the flag the moment it flips', async () => {
		integrationStatus.value = baseStatus()
		server.status = {
			...baseStatus(),
			zoom: { ...baseStatus().zoom, attendance: false },
		}
		const wrapper = mount(ZoomAttendanceSwitch, mountOptions)
		const toggle = wrapper.get('[data-testid="zoom-attendance"]')
		expect(toggle.attributes('aria-checked')).toBe('true')
		await toggle.trigger('click')
		await flushPromises()
		expect(server.calls).toEqual([
			{ url: SAVE_URL, params: { changes: { zoom_attendance: false } } },
		])
		expect(toggle.attributes('aria-checked')).toBe('false')
	})
})
