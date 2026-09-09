import { call, toast } from 'frappe-ui'
import { markRaw } from 'vue'
// @ts-expect-error router.js is still plain JS, so it has no declarations
import router from '@/router'
// @ts-expect-error utils/dialogs.js is still plain JS, so it has no declarations
import { createDialog } from '@/utils/dialogs'
import Transactions from '@/components/Settings/Transactions/Transactions.vue'
import { usePermissions } from '@/composables/usePermissions'
import {
	reloadSettingsLists,
	type SettingsListFilters,
	type SettingsListResourceOptions,
} from '@/composables/useSettingsListResource'
import type { CustomPage, SelectOption } from '@/types/settingsSchema'
import type {
	DropdownOption,
	SettingsListColumn,
	SettingsListRow,
} from '@/types'

/**
 * Settings > Payment > Transactions, as data: what the LMS Payment list fetches,
 * the columns it draws, the filter above it and the labels the record page uses.
 * Transactions.vue draws all of it — the list and the record — and this module
 * is what it draws it from.
 *
 * Every translated string here is produced inside a function or a getter, never
 * as a plain property. `__` is installed on window by translationPlugin, which
 * runs after main.js has finished importing the settings tree — a `__()` call at
 * module scope would throw, and would read the translations before they have
 * loaded even if it did not.
 */

export const DOCTYPE = 'LMS Payment'

/** What the list fetches: the columns' fields, and nothing the record page reloads anyway. */
export const transactionList: SettingsListResourceOptions = {
	doctype: DOCTYPE,
	fields: [
		'name',
		'member',
		'billing_name',
		'payment_for_document_type',
		'payment_for_document',
		'payment_received',
		'payment_for_certificate',
		'currency',
		'amount',
	],
	searchFields: ['billing_name', 'member'],
	orderBy: 'modified desc',
}

/**
 * Which fields the doctype declares mandatory, as the create form's fallback.
 *
 * The server's own answer — get_payment_field_meta — wins wherever it has one,
 * because a site is free to relax or tighten `reqd` on any of them. This is what
 * the form marks required while that answer is still in flight, or if it fails.
 */
export const REQUIRED_FIELDS = [
	'member',
	'billing_name',
	'source',
	'payment_for_document_type',
	'payment_for_document',
	'currency',
	'amount',
	'address',
]

export const FIELD_META_METHOD = 'lms.lms.api.get_payment_field_meta'

/**
 * The fields on LMS Payment the record page reads rather than offers.
 *
 * `coupon_code` is the doctype's only `read_only` field, and the only one it
 * fetches from another document: `fetch_from: coupon.code` is re-read out of
 * the linked LMS Coupon on every save, so a value typed over it would be
 * discarded on the way to the database. Everything else the doctype declares —
 * amount, currency, the gateway ids, member, address, member_consent — carries
 * neither flag and has no server-side recomputation behind it (LMSPayment
 * declares no validate, and hooks.py registers no doc_events for it), so it is
 * writable and is drawn as a control.
 *
 * `billing_name` looks fetched and is not. Its `fetch_from` names a link field
 * called `user`, which LMS Payment does not have — frappe resolves a fetch
 * against the link field the path starts at, so nothing is ever fetched into
 * it and what a moderator types there is what is saved.
 */
export const READ_ONLY_FIELDS = ['coupon_code']

const CURRENCY_SYMBOLS: Record<string, string> = {
	USD: '$',
	EUR: '€',
	GBP: '£',
	INR: '₹',
	AED: 'د.إ',
	CHF: 'Fr',
	JPY: '¥',
	AUD: '$',
}

/** The row's money, drawn identically in the list cell and on the record page. */
export const formatAmount = (
	amount: unknown,
	currency: string | undefined
): string => {
	if (amount === null || amount === undefined || amount === '') return ''
	const symbol = currency ? CURRENCY_SYMBOLS[currency] || currency : ''
	return symbol ? `${symbol} ${amount}` : String(amount)
}

/**
 * What a payment can be for, for the record page's picker and for naming the
 * document a payment paid for. The doctype's own Select offers exactly these
 * two.
 */
export const documentTypeOptions = (): SelectOption[] => [
	{ label: __('Course'), value: 'LMS Course' },
	{ label: __('Batch'), value: 'LMS Batch' },
]

export const documentTypeLabel = (doctype: string): string =>
	documentTypeOptions().find((option) => option.value === doctype)?.label ||
	doctype

/**
 * The filter above the list, restored: it was dropped when this page became a
 * ListPage, because the shared panel's filter sends its value as a request
 * parameter and a doctype list takes server-side `filters` instead.
 *
 * Same five choices the page carried before — the two the Status column draws,
 * and what the payment was for.
 */
export const STATUS_ALL = 'All'

export const statusOptions = (): SelectOption[] => [
	{ label: __('All Payments'), value: STATUS_ALL },
	{ label: __('Paid'), value: 'Paid' },
	{ label: __('Unpaid'), value: 'Unpaid' },
	{ label: __('For Certificate'), value: 'Certificate' },
	{ label: __('For Course'), value: 'Course' },
]

export const statusFilters = (status: string): SettingsListFilters => {
	switch (status) {
		case 'Paid':
			return [['payment_received', '=', 1]]
		case 'Unpaid':
			return [['payment_received', '=', 0]]
		case 'Certificate':
			return [['payment_for_certificate', '=', 1]]
		case 'Course':
			return [['payment_for_certificate', '=', 0]]
		default:
			return []
	}
}

/**
 * Where a paid-for document opens, and what the row menu calls it.
 *
 * The label is one whole string per document type. It used to be
 * `__('Open the ') + doctype`, which hands the translator a dangling fragment
 * and glues an untranslated doctype name onto it — unreadable in any language
 * that inflects the noun after "the", and untranslatable in one that puts the
 * article elsewhere.
 *
 * A payment for anything else offers nothing rather than falling through to the
 * batch route, which is what the old ternary did.
 */
const OPENERS: Record<
	string,
	{ label: () => string; route: (name: string) => object }
> = {
	'LMS Course': {
		label: () => __('Open the Course'),
		route: (name) => ({ name: 'CourseDetail', params: { courseName: name } }),
	},
	'LMS Batch': {
		label: () => __('Open the Batch'),
		route: (name) => ({ name: 'BatchDetail', params: { batchName: name } }),
	},
}

// One handle per record, because usePermissions registers a watcher and this is
// called from a render. The answers themselves are cached inside the composable
// and asked for in one batched request per tick, so a page of rows costs one
// round trip.
const handles = new Map<string, ReturnType<typeof usePermissions>>()

/**
 * Whether the server says this user may delete this payment.
 *
 * The permission is the doctype's, not a role guess: LMS Payment grants delete
 * to System Manager and Moderator, and a site that has changed that is answered
 * correctly here. `can()` reads false until the answer arrives, so the option
 * appears rather than disappears.
 */
const canDelete = (name: string): boolean => {
	if (!name) return false
	let handle = handles.get(name)
	if (!handle) {
		handle = usePermissions(DOCTYPE, name)
		handles.set(name, handle)
	}
	return handle.can('delete')
}

const removeTransaction = (name: string, close: () => void) => {
	call('frappe.client.delete', { doctype: DOCTYPE, name })
		.then(() => {
			toast.success(__('Transaction deleted successfully'))
			if (typeof close === 'function') close()
			return reloadSettingsLists(DOCTYPE)
		})
		.catch((error: { messages?: string[] }) => {
			toast.error(error?.messages?.[0] || __('Unable to delete transaction'))
			console.error(error)
		})
}

// Same confirmation the other settings lists put a delete behind (Categories,
// Coupons): a red solid Delete in a dialog that says what is lost.
const confirmDeletion = (row: SettingsListRow) => {
	createDialog({
		title: __('Delete this transaction?'),
		message: __(
			'This will permanently delete this payment record, including its billing details. This cannot be undone.'
		),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick({ close }: { close: () => void }) {
					removeTransaction(row.name, close)
				},
			},
		],
	})
}

const rowOptions = (row: SettingsListRow): DropdownOption[] => {
	const options: DropdownOption[] = []

	const opener = OPENERS[row.payment_for_document_type]
	if (opener && row.payment_for_document)
		options.push({
			label: opener.label(),
			icon: 'lucide-external-link',
			// Pushing a route with no hash leaves the settings hash behind, which
			// is what closes the dialog. The record page carries no such button:
			// it would route out of the dialog it is drawn inside.
			onClick: () => router.push(opener.route(row.payment_for_document)),
		})

	if (canDelete(row.name))
		options.push({
			label: __('Delete'),
			icon: 'lucide-trash-2',
			onClick: () => confirmDeletion(row),
		})

	return options
}

export const columns: SettingsListColumn[] = [
	{
		key: 'billing_name',
		get label() {
			return __('Billing Name')
		},
		type: 'stacked',
		primary: (row) => row.billing_name,
		secondary: (row) => row.member,
	},
	{
		key: 'amount',
		get label() {
			return __('Amount')
		},
		type: 'text',
		width: '8rem',
		value: (row) => formatAmount(row.amount, row.currency),
	},
	{
		key: 'status',
		get label() {
			return __('Status')
		},
		type: 'badge',
		width: '10rem',
		badges: (row) => {
			const badges = []
			// An unpaid row used to draw nothing here, so a transaction awaiting
			// payment was indistinguishable from one whose status had not loaded.
			badges.push(
				row.payment_received
					? { label: __('Paid'), theme: 'green' as const }
					: { label: __('Unpaid'), theme: 'orange' as const }
			)
			if (row.payment_for_certificate)
				badges.push({ label: __('Certificate'), theme: 'blue' as const })
			return badges
		},
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) =>
			__('Actions for {0}').format(row.billing_name || row.name),
		options: rowOptions,
	},
]

export const transactionsPage: CustomPage = {
	kind: 'custom',
	/**
	 * A getter, not `markRaw(Transactions)` on the spot: Transactions.vue imports
	 * this module for the config above, so the two modules form a cycle and
	 * whichever is entered second is still initialising when the other reads it.
	 * Reading the component here is deferred to the render, by which time both
	 * have finished.
	 */
	get component() {
		return markRaw(Transactions)
	},
}
