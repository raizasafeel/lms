import { reactive, ref } from 'vue'
import { call, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import { reportSaveFailure } from '@/composables/useSettingsSource'
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
	| 'flow'

/** What lms.lms.integrations.get_integration_status answers. */
export interface IntegrationStatus {
	google: { enabled: boolean; has_credentials: boolean; permitted: boolean }
	google_calendar: { enabled: boolean; calendars: number; need_access: number }
	google_meet: { enabled: boolean; accounts: number }
	zoom: { enabled: boolean; attendance: boolean; accounts: number }
	code_runner: { enabled: boolean; own_server: boolean }
	unsplash: { enabled: boolean; has_key: boolean }
	raven: { enabled: boolean; raven: boolean; raven_integration: boolean }
	flow: {
		installed: boolean
		enabled: boolean
		hide_for_learners: boolean
		ready: boolean
	}
}

export type IntegrationChanges = Partial<Record<IntegrationKey, boolean>>

/** A fix for what the card is missing: its Configure page, or its records page. */
export interface CardAction {
	label: string
	opens: 'configure' | 'records'
	/** A record on the records page to open, such as 'new' for a create form. */
	record?: string
}

export interface CardLine {
	label: string
	warning?: boolean
	/** Shown as a button in place of the warning. */
	action?: CardAction
}

export interface Integration {
	key: IntegrationKey
	/** English; the card translates it on render. */
	label: string
	icon: string
	description: string
	/** Configure opens a page of fields inside the grid. */
	configure?: true
	/** The integration's own sidebar page of records, and what its button reads (English). */
	records?: { slug: string; label: string }
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

/** Flipped and being written; shown at once and dropped when the write settles. */
const pendingSwitches = reactive<IntegrationChanges>({})

export const isSwitchOn = (key: IntegrationKey): boolean =>
	pendingSwitches[key] ?? isIntegrationEnabled(key)

/** Saves a switch the moment it flips; a refusal puts it back. */
export const toggleIntegration = async (
	key: IntegrationKey,
	value: boolean
): Promise<void> => {
	if (key in pendingSwitches) return
	pendingSwitches[key] = value
	try {
		await saveIntegrations({ [key]: value })
		toast.success(value ? __('Turned on') : __('Turned off'))
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
		await loadIntegrationStatus()
	} finally {
		delete pendingSwitches[key]
	}
}

/** The cards in the Integrations grid. */
export const integrations: Integration[] = [
	{
		key: 'google',
		label: 'Google',
		icon: 'lucide-key-round',
		description: 'Lets the school use Google Calendar and Google Meet.',
		configure: true,
	},
	{
		key: 'zoom',
		label: 'Zoom',
		icon: 'lucide-video',
		description: 'Creates a Zoom link for each live class.',
		configure: true,
		records: { slug: 'zoom', label: 'Accounts' },
	},
	{
		key: 'code_runner',
		label: 'Code runner',
		icon: 'lucide-square-terminal',
		description: "Runs learners' code in programming exercises.",
		configure: true,
	},
	{
		key: 'unsplash',
		label: 'Unsplash',
		icon: 'lucide-image',
		description: 'Lets people pick cover images from Unsplash.',
		configure: true,
	},
	{
		key: 'raven',
		label: 'Raven',
		icon: 'lucide-messages-square',
		description:
			'Puts learners in a chat channel for each batch and posts announcements there.',
		records: { slug: 'raven', label: 'Workspaces' },
	},
	{
		key: 'flow',
		label: 'Flow',
		icon: 'lucide-sparkles',
		description:
			'AI assistant beside the app for building courses and answering questions.',
		configure: true,
	},
]

/** Switched on and off inside Google's Configure page. */
export const googleServices: Integration[] = [
	{
		key: 'google_calendar',
		label: 'Google Calendar',
		icon: 'lucide-calendar',
		description:
			"Books evaluations into evaluators' free slots and sends invites.",
		records: { slug: 'google-calendar', label: 'Calendars' },
	},
	{
		key: 'google_meet',
		label: 'Google Meet',
		icon: 'lucide-presentation',
		description: 'Creates a Meet link for each live class and evaluation.',
		records: { slug: 'google-meet', label: 'Accounts' },
	},
]

export const isIntegrationEnabled = (key: IntegrationKey): boolean => {
	const state = integrationStatus.value?.[key]
	return Boolean(state && 'enabled' in state && state.enabled)
}

/**
 * A sidebar item tied to an integration shows once it is on. Hidden
 * until the status loads, so a disabled page never flashes in.
 */
export const isSidebarItemVisible = (item: {
	integration?: IntegrationKey
}): boolean => !item.integration || isIntegrationEnabled(item.integration)

/** The next app to install: its step as the status (English), and its button. */
export interface MissingApp {
	label: string
	action: string
	url: string
}

/** Raven comes first; the integration app builds on it. Null when nothing is missing. */
export const missingApp = (
	key: IntegrationKey,
	status: IntegrationStatus
): MissingApp | null => {
	if (key === 'raven' && !status.raven.raven)
		return {
			label: 'Step 1 of 2',
			action: 'Install Raven',
			url: 'https://cloud.frappe.io/marketplace/apps/raven',
		}
	if (key === 'raven' && !status.raven.raven_integration)
		return {
			label: 'Step 2 of 2',
			action: 'Install Raven integration',
			url: 'https://github.com/raizasafeel/raven_integration',
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

const fix = (
	label: string,
	opens: CardAction['opens'],
	record?: string
): CardAction => ({ label: __(label), opens, record })

/** A create form skips the list's dependency banner, so it opens only once met. */
const accountsLine = (accounts: number, canCreate: boolean): CardLine =>
	accounts
		? { label: plural(accounts, '1 account', '{0} accounts') }
		: {
				label: __('No accounts yet'),
				warning: true,
				action: fix('Add an account', 'records', canCreate ? 'new' : undefined),
		  }

const calendarLine = (status: IntegrationStatus): CardLine => {
	const state = status.google_calendar
	if (!state.calendars)
		return {
			label: __('No calendars yet'),
			warning: true,
			action: fix(
				'Add a calendar',
				'records',
				isGoogleConnected(status) ? 'new' : undefined
			),
		}
	const calendars = plural(state.calendars, '1 calendar', '{0} calendars')
	if (!state.need_access) return { label: calendars }
	return {
		label: `${calendars} · ${__('{0} need access').format(
			String(state.need_access)
		)}`,
		warning: true,
		action: fix('Grant calendar access', 'records'),
	}
}

const zoomLine = (state: IntegrationStatus['zoom']): CardLine => {
	const accounts = accountsLine(state.accounts, true)
	const attendance = state.attendance
		? __('attendance on')
		: __('attendance off')
	return { ...accounts, label: `${accounts.label} · ${attendance}` }
}

const flowLine = (state: IntegrationStatus['flow']): CardLine => {
	if (!state.ready)
		return {
			label: __('No AI service connected'),
			warning: true,
			action: fix('Connect an AI service', 'configure'),
		}
	return {
		label: state.hide_for_learners
			? __('Connected · hidden for learners')
			: __('Connected'),
	}
}

const onLines: Record<IntegrationKey, (status: IntegrationStatus) => CardLine> =
	{
		google: (status) =>
			status.google.has_credentials
				? { label: __('Connected') }
				: {
						label: __('Needs a client ID and secret'),
						warning: true,
						action: fix('Set up client ID and secret', 'configure'),
				  },
		google_calendar: (status) => calendarLine(status),
		google_meet: (status) =>
			accountsLine(
				status.google_meet.accounts,
				isGoogleConnected(status) && status.google_calendar.calendars > 0
			),
		zoom: (status) => zoomLine(status.zoom),
		code_runner: (status) => ({
			label: status.code_runner.own_server
				? __('Your own server')
				: __("Frappe's server"),
		}),
		unsplash: (status) =>
			status.unsplash.has_key
				? { label: __('Connected') }
				: {
						label: __('Needs an access key'),
						warning: true,
						action: fix('Add access key', 'configure'),
				  },
		raven: () => ({ label: __('Connected') }),
		flow: (status) => flowLine(status.flow),
	}

/** The status line under a card, for the state it would be in once saved. */
export const statusLine = (
	key: IntegrationKey,
	status: IntegrationStatus,
	enabled: boolean
): CardLine => {
	const missing = missingApp(key, status)
	if (missing) return { label: __(missing.label) }
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
	key: IntegrationKey,
	status: IntegrationStatus,
	pending: { enabled: (key: IntegrationKey) => boolean }
): string => {
	if (needsGoogleRole(key, status)) return __('Needs the System Manager role')
	if (key === 'flow' && !status.flow.installed)
		return __('This version of Frappe has no Flow')
	if (key === 'raven' && status.raven.enabled)
		return __("Raven membership sync can't be turned off once it is on.")
	const needsGoogle = key === 'google_calendar' || key === 'google_meet'
	if (needsGoogle && !isGoogleReady(status, pending) && !pending.enabled(key))
		return __('Turn Google on and save its client ID and secret first')
	return ''
}

/** lockedReason, or that the switch is still saving. */
export const switchLockedReason = (
	key: IntegrationKey,
	status: IntegrationStatus
): string =>
	key in pendingSwitches
		? __('Saving…')
		: lockedReason(key, status, { enabled: isSwitchOn })

/** Google is on and has the client ID and secret Calendar and Meet sign in with. */
const isGoogleReady = (
	status: IntegrationStatus,
	pending: { enabled: (key: IntegrationKey) => boolean }
): boolean => pending.enabled('google') && status.google.has_credentials

const isGoogleConnected = (status: IntegrationStatus): boolean =>
	status.google.enabled && status.google.has_credentials

/** Pages that hold what an integration needs before it can work. */
const SETUP_PAGES: IntegrationKey[] = ['google', 'code_runner', 'unsplash']

const isUsable = (key: IntegrationKey, status: IntegrationStatus): boolean =>
	!missingApp(key, status) && !needsGoogleRole(key, status)

/**
 * Configure opens whenever the integration is on, and also while it is off
 * for one whose page holds its credentials, so they can go in first.
 */
export const isConfigurable = (
	integration: Integration,
	status: IntegrationStatus
): boolean =>
	Boolean(integration.configure) &&
	isUsable(integration.key, status) &&
	(isIntegrationEnabled(integration.key) ||
		SETUP_PAGES.includes(integration.key))

/** The records page opens when the sidebar lists it: once the integration is on. */
export const hasRecordsAvailable = (
	integration: Integration,
	status: IntegrationStatus
): boolean =>
	Boolean(integration.records) &&
	isUsable(integration.key, status) &&
	isIntegrationEnabled(integration.key)
