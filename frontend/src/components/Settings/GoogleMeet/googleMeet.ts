import { defineAsyncComponent, markRaw } from 'vue'
import { call, toast } from 'frappe-ui'
import { usersStore } from '@/stores/user'
import { reloadSettingsLists } from '@/composables/useSettingsListResource'
import { cleanError } from '@/utils'
import type { ListPage } from '@/types/settingsSchema'
import type { SettingsListColumn, SettingsListRow } from '@/types'

/**
 * Google Meet accounts: the list, as data, and one component for the account
 * behind a row. What lives here is only what is Google Meet's, and
 * SettingsListPanel does the rest, as it does for every list.
 */

const DOCTYPE = 'LMS Google Meet Settings'

// `autoname: field:account_name`, so a row's doc name IS its account name.
// Both are read because a deep link can open a record the list has not fetched.
const accountLabel = (row: SettingsListRow): string =>
	row.account_name || row.name || ''

// `member_name` is fetched from the member's full_name, which a User is not
// obliged to have. The email is then the only name the row has.
const memberLabel = (row: SettingsListRow): string =>
	row.member_name || row.member || ''

/**
 * Whose accounts this page shows. A moderator sees the site's, anyone else sees
 * their own. It is an access control, not a display filter. Read through the
 * store lazily, because pinia is installed after this module is evaluated.
 */
export const memberScope = (): Record<string, unknown> => {
	const { userResource } = usersStore()
	const user = userResource?.data
	return user?.is_moderator ? {} : { member: user?.name }
}

/**
 * Whether the page belongs in the sidebar at all. The component this replaces
 * refused to fetch for a user who was neither a moderator nor an evaluator, and
 * a page has no say in whether its item is listed.
 */
export const canManageGoogleMeet = (): boolean => {
	const { userResource } = usersStore()
	const user = userResource?.data
	return Boolean(user?.is_moderator || user?.is_evaluator)
}

/**
 * Optimistic, with a rollback. The row flips under the pointer and the write
 * follows it. Nothing reloads the list here, so without the rollback a rejected
 * write would leave the row showing a state the server refused.
 */
const toggleEnabled = async (row: SettingsListRow, value: boolean) => {
	const previous = row.enabled
	row.enabled = value ? 1 : 0
	try {
		await call('frappe.client.set_value', {
			doctype: DOCTYPE,
			name: row.name,
			fieldname: 'enabled',
			value: row.enabled,
		})
	} catch (err: any) {
		row.enabled = previous
		toast.error(cleanError(err.messages?.[0] || err))
	}
}

/**
 * The row menu's Delete. A config module is handed the row and nothing else, so
 * it asks every list on screen for that doctype to refetch, which also keeps the
 * list on its first page.
 */
const removeAccount = async (row: SettingsListRow) => {
	try {
		await call('frappe.client.delete', { doctype: DOCTYPE, name: row.name })
		toast.success(__('Google Meet account deleted successfully'))
		await reloadSettingsLists(DOCTYPE)
	} catch (err: any) {
		toast.error(cleanError(err.messages?.[0] || err))
	}
}

// Every header is a getter, because `__` is installed on window only after every
// static import has been evaluated. The account and its member share one
// `stacked` column, since a column of its own said nothing the first did not.
const columns: SettingsListColumn[] = [
	{
		key: 'account',
		get label() {
			return __('Account')
		},
		type: 'stacked',
		primary: (row) => accountLabel(row),
		secondary: (row) => memberLabel(row),
		avatar: (row) => ({ image: row.member_image, label: memberLabel(row) }),
	},
	{
		key: 'calendar',
		get label() {
			return __('Google Calendar')
		},
		type: 'text',
		value: (row) => row.google_calendar || '',
	},
	{
		key: 'enabled',
		get label() {
			return __('Enabled')
		},
		type: 'switch',
		width: '6.5rem',
		checked: (row) => Boolean(row.enabled),
		ariaLabel: (row) => __('Enable {0}').format(accountLabel(row)),
		onChange: toggleEnabled,
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) => __('Actions for {0}').format(accountLabel(row)),
		options: (row) => [
			{
				label: __('Delete'),
				icon: 'lucide-trash-2',
				onClick: () => removeAccount(row),
			},
		],
	},
]

/**
 * One component for New and for an existing account alike, handed the record the
 * panel opened. A `kind: 'custom'` detail rather than a fields page, because the
 * account name is the document's own name. Loaded on demand, the way Zoom is.
 */
const accountForm = {
	kind: 'custom' as const,
	component: markRaw(
		defineAsyncComponent(() => import('./GoogleMeetAccountForm.vue'))
	),
}

export const googleMeetSettingsPage: ListPage = {
	kind: 'list',
	resource: {
		doctype: DOCTYPE,
		fields: [
			'name',
			'enabled',
			'account_name',
			'member',
			'member_name',
			'member_image',
			'google_calendar',
		],
		// A getter, read once by the panel at setup. The signed-in user is not loaded
		// when this module is first imported, which is why the component this
		// replaces applied the filter from onMounted.
		get filters() {
			return memberScope()
		},
		searchFields: ['account_name', 'member_name', 'google_calendar'],
	},
	columns,
	searchable: true,
	empty: { name: 'Google Meet Settings', icon: 'lucide-presentation' },
	create: { detail: accountForm },
	rowDetail: accountForm,
}
