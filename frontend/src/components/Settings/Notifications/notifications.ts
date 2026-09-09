import { defineAsyncComponent, markRaw } from 'vue'
import { call, toast } from 'frappe-ui'
import { cleanError } from '@/utils'
import type { DetailPage, ListPage, SelectOption } from '@/types/settingsSchema'
import type { SettingsListColumn, SettingsListRow } from '@/types'

/**
 * Settings > Notifications, as config: every mail Frappe Learning sends, as the
 * Notification rules that send them. Read through two gated LMS endpoints,
 * because core Notification grants DocPerms to System Manager only.
 */

// Writing `subject` or `message` needs System Manager on top of that. A rule's
// message renders as Jinja with an unchecked read-anything namespace, so a
// Moderator is limited to enabled, channel and send_system_notification.

export const METHOD = {
	list: 'lms.lms.api.get_notification_rules',
	set: 'lms.lms.api.set_notification_rule',
} as const

// Not a real doctype resource. This is the key `reloadSettingsLists` refetches
// the list by, the same way Email Accounts carries `Email Account` alongside
// its own `method`.
export const NOTIFICATIONS_DOCTYPE = 'Notification'

export const NOTIFICATION_RULE_FIELDS = [
	'name',
	'enabled',
	'channel',
	'send_system_notification',
	'subject',
	'message',
]

/**
 * The only two channels LMS can honour. Notification.channel also offers Slack
 * and SMS, but no send path exists for either, so the picker never offers them
 * and the endpoint refuses a write naming one.
 */
export const channelOptions = (): SelectOption[] => [
	{ label: __('Email'), value: 'Email' },
	{ label: __('In-app'), value: 'System Notification' },
]

/** What the "Sent via" column reads, from the same two values the picker writes. */
export const channelLabel = (row: SettingsListRow): string => {
	if (row.channel === 'Email')
		return row.send_system_notification ? __('Email + In-app') : __('Email')
	return __('In-app')
}

/**
 * The Enabled switch's write. Optimistic, with a rollback: the row flips under
 * the pointer and a refused write puts it back to what the server still holds.
 */
const toggleEnabled = async (row: SettingsListRow, value: boolean) => {
	const previous = row.enabled
	row.enabled = value ? 1 : 0
	try {
		await call(METHOD.set, { name: row.name, enabled: row.enabled })
	} catch (err: any) {
		row.enabled = previous
		toast.error(cleanError(err.messages?.[0] || err) || __('Could not save'))
	}
}

const columns: SettingsListColumn[] = [
	{
		key: 'notification',
		get label() {
			return __('Notification')
		},
		type: 'stacked',
		primary: (row) => row.name,
		secondary: (row) => row.subject,
	},
	{
		key: 'channel',
		get label() {
			return __('Sent via')
		},
		type: 'badge',
		width: '11rem',
		badges: (row) => [{ label: channelLabel(row), theme: 'gray' }],
	},
	{
		key: 'enabled',
		get label() {
			return __('Enabled')
		},
		type: 'switch',
		width: '6.5rem',
		checked: (row) => Boolean(row.enabled),
		ariaLabel: (row) => __('Enable {0}').format(row.name),
		onChange: toggleEnabled,
	},
]

// Loaded on demand and kept apart from the list, the way every other record
// page in Settings is. A static import would close a cycle the moment the
// record needs anything from here.
const record: DetailPage = {
	kind: 'custom',
	component: markRaw(
		defineAsyncComponent(
			() => import('@/components/Settings/Notifications/NotificationRecord.vue')
		)
	),
}

export const notificationsPage: ListPage = {
	kind: 'list',
	resource: {
		doctype: NOTIFICATIONS_DOCTYPE,
		// Read by the endpoint, not by a get_list call, because it applies its own
		// role gate and `module = "LMS"` scope. All twelve rules come back at once,
		// so the page length is set past anything the catalogue will reach.
		method: METHOD.list,
		fields: NOTIFICATION_RULE_FIELDS,
		pageLength: 100,
	},
	columns,
	searchable: true,
	empty: { name: 'Notifications', icon: 'lucide-bell' },
	// No `create`: every rule is seeded by lms.lms.notifications.seed_notifications
	// and none can be deleted, so there is nothing for a New affordance to do.
	rowDetail: record,
}
