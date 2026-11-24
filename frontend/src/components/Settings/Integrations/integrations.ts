import { ref } from 'vue'
import { call } from 'frappe-ui'
import { hasCloudSettings } from '@/composables/cloudSettings'
import { openExternal } from '@/utils/openExternal'

export type IntegrationKey =
	| 'google'
	| 'google_calendar'
	| 'google_meet'
	| 'zoom'
	| 'code_runner'
	| 'unsplash'
	| 'raven'
	| 'frappe_meet'

/** What lms.lms.integrations.get_integration_status answers. */
export interface IntegrationStatus {
	google: { enabled: boolean; has_credentials: boolean; permitted: boolean }
	google_calendar: { enabled: boolean; calendars: number; need_access: number }
	google_meet: { enabled: boolean; accounts: number }
	zoom: { enabled: boolean; attendance: boolean; accounts: number }
	code_runner: { enabled: boolean; own_server: boolean }
	unsplash: { enabled: boolean; has_key: boolean }
	raven: { enabled: boolean; raven: boolean; raven_integration: boolean }
	frappe_meet: { installed: boolean }
}

export type ToggleKey = Exclude<IntegrationKey, 'frappe_meet'>
export type IntegrationChanges = Partial<
	Record<ToggleKey | 'zoom_attendance', boolean>
>

export interface CardLine {
	label: string
	warning?: boolean
}

export interface Integration {
	key: IntegrationKey
	/** English; the card translates it on render. */
	label: string
	icon: string
	description: string
	/** The settings page Configure opens. */
	slug?: string
}

const STATUS_URL = 'lms.lms.integrations.get_integration_status'
const SAVE_URL = 'lms.lms.integrations.set_integrations_enabled'

/** The one copy of every integration's state, shared by the grid and the sidebar. */
export const integrationStatus = ref<IntegrationStatus | null>(null)

export const loadIntegrationStatus = async (): Promise<void> => {
	integrationStatus.value = await call(STATUS_URL)
}

export const saveIntegrations = async (
	changes: IntegrationChanges
): Promise<void> => {
	integrationStatus.value = await call(SAVE_URL, { changes })
}

export const integrations: Integration[] = [
	{
		key: 'google',
		label: 'Google',
		icon: 'lucide-key-round',
		description: 'Lets the school use Google Calendar and Google Meet.',
		slug: 'services',
	},
	{
		key: 'google_calendar',
		label: 'Google Calendar',
		icon: 'lucide-calendar',
		description:
			"Books evaluations into evaluators' free slots and sends invites.",
		slug: 'google-calendar',
	},
	{
		key: 'google_meet',
		label: 'Google Meet',
		icon: 'lucide-presentation',
		description: 'Creates a Meet link for each live class and evaluation.',
		slug: 'google-meet',
	},
	{
		key: 'zoom',
		label: 'Zoom',
		icon: 'lucide-video',
		description: 'Creates a Zoom link for each live class.',
		slug: 'zoom',
	},
	{
		key: 'code_runner',
		label: 'Code runner',
		icon: 'lucide-square-terminal',
		description: "Runs learners' code in programming exercises.",
		slug: 'services',
	},
	{
		key: 'unsplash',
		label: 'Unsplash',
		icon: 'lucide-image',
		description: 'Lets people pick cover images from Unsplash.',
		slug: 'services',
	},
	{
		key: 'raven',
		label: 'Raven',
		icon: 'lucide-messages-square',
		description:
			'Puts learners in a chat channel for each batch and posts announcements there.',
		slug: 'raven',
	},
	{
		key: 'frappe_meet',
		label: 'Frappe Meet',
		icon: 'lucide-phone-call',
		description:
			'Runs live classes and evaluations on your own video calls, with no Zoom or Google account.',
	},
]

export const isIntegrationEnabled = (key: IntegrationKey): boolean => {
	const state = integrationStatus.value?.[key]
	return Boolean(state && 'enabled' in state && state.enabled)
}

/**
 * A sidebar item tied to integrations shows once any of them is on. Hidden
 * until the status loads, so a disabled page never flashes in.
 */
export const isSidebarItemVisible = (item: {
	integration?: IntegrationKey | IntegrationKey[]
}): boolean => {
	if (!item.integration) return true
	const keys = Array.isArray(item.integration)
		? item.integration
		: [item.integration]
	return keys.some(isIntegrationEnabled)
}

/** The app an integration still needs, or null when nothing is missing. */
export const missingApp = (
	key: IntegrationKey,
	status: IntegrationStatus
): { label: string; url: string } | null => {
	if (key === 'raven' && !status.raven.raven_integration)
		return {
			label: 'Needs the Raven integration app',
			url: 'https://github.com/raizasafeel/raven_integration',
		}
	if (key === 'raven' && !status.raven.raven)
		return {
			label: 'Needs the Raven app',
			url: 'https://cloud.frappe.io/marketplace/apps/raven',
		}
	if (key === 'frappe_meet' && !status.frappe_meet.installed)
		return {
			label: 'Needs the Frappe Meet app',
			url: 'https://cloud.frappe.io/marketplace/apps/meet',
		}
	return null
}

/** On Frappe Cloud the marketplace opens inside Settings; elsewhere, its page. */
export const installApp = (
	url: string,
	openSettings: (slug: string) => void
): void => {
	if (hasCloudSettings() && url.includes('/marketplace/')) {
		openSettings('cloud-marketplace')
	} else {
		openExternal(url)
	}
}

const plural = (count: number, one: string, many: string): string =>
	count === 1 ? __(one) : __(many).format(String(count))

const accountsLine = (accounts: number): CardLine =>
	accounts
		? { label: plural(accounts, '1 account', '{0} accounts') }
		: { label: __('No accounts yet'), warning: true }

const calendarLine = (
	state: IntegrationStatus['google_calendar']
): CardLine => {
	if (!state.calendars) return { label: __('No calendars yet'), warning: true }
	const calendars = plural(state.calendars, '1 calendar', '{0} calendars')
	if (!state.need_access) return { label: calendars }
	return {
		label: `${calendars} · ${__('{0} need access').format(
			String(state.need_access)
		)}`,
		warning: true,
	}
}

const zoomLine = (state: IntegrationStatus['zoom']): CardLine => {
	const accounts = accountsLine(state.accounts)
	const attendance = state.attendance
		? __('attendance on')
		: __('attendance off')
	return { ...accounts, label: `${accounts.label} · ${attendance}` }
}

const onLines: Record<ToggleKey, (status: IntegrationStatus) => CardLine> = {
	google: (status) =>
		status.google.has_credentials
			? { label: __('Connected') }
			: { label: __('Needs a client ID and secret'), warning: true },
	google_calendar: (status) => calendarLine(status.google_calendar),
	google_meet: (status) => accountsLine(status.google_meet.accounts),
	zoom: (status) => zoomLine(status.zoom),
	code_runner: (status) => ({
		label: status.code_runner.own_server
			? __('Your own server')
			: __("Frappe's server"),
	}),
	unsplash: (status) =>
		status.unsplash.has_key
			? { label: __('Connected') }
			: { label: __('Needs an access key'), warning: true },
	raven: () => ({ label: __('Connected') }),
}

/** The status line under a card, for the state it would be in once saved. */
export const statusLine = (
	key: IntegrationKey,
	status: IntegrationStatus,
	enabled: boolean
): CardLine => {
	const missing = missingApp(key, status)
	if (missing) return { label: __(missing.label) }
	if (key === 'frappe_meet') return { label: __('Installed') }
	if (needsGoogleRole(key, status))
		return { label: __('Needs the System Manager role'), warning: true }
	if (!enabled) return { label: __('Off') }
	return onLines[key](status)
}

const GOOGLE_ADMIN_ONLY: IntegrationKey[] = ['google', 'google_calendar']

export const needsGoogleRole = (
	key: IntegrationKey,
	status: IntegrationStatus
): boolean => GOOGLE_ADMIN_ONLY.includes(key) && !status.google.permitted

/** Why a card's switch can't be flipped right now, or '' when it can. */
export const lockedReason = (
	key: ToggleKey,
	status: IntegrationStatus,
	pending: { enabled: (key: ToggleKey) => boolean }
): string => {
	if (needsGoogleRole(key, status)) return __('Needs the System Manager role')
	if (key === 'raven' && status.raven.enabled)
		return __("Raven membership sync can't be turned off once it is on.")
	const needsGoogle = key === 'google_calendar' || key === 'google_meet'
	if (needsGoogle && !pending.enabled('google') && !pending.enabled(key))
		return __('Turn on Google first')
	return ''
}
