import { markRaw } from 'vue'
import { call, toast } from 'frappe-ui'
// @ts-expect-error utils/dialogs.js is still plain JS, so it has no declarations
import { createDialog } from '@/utils/dialogs'
import EmailTemplates from '@/components/Settings/EmailTemplate/EmailTemplates.vue'
import { reloadSettingsLists } from '@/composables/useSettingsListResource'
import { deleteRow } from '@/components/Settings/rowActions'
import { cleanError } from '@/utils'
import type { CustomPage } from '@/types/settingsSchema'
import type { SettingsListColumn, SettingsListRow } from '@/types'

/**
 * Email templates, as config: what the list fetches, what it shows, and what its
 * row menu does. EmailTemplates.vue draws the list and the record alike.
 */

export const DOCTYPE = 'Email Template'

/** What the list fetches, and what the record page and Duplicate both read. */
export const TEMPLATE_FIELDS = [
	'name',
	'subject',
	'use_html',
	'response',
	'response_html',
]

export const TEMPLATE_SEARCH_FIELDS = ['name', 'subject']

export const TEMPLATE_ORDER_BY = 'modified desc'

const removeTemplate = deleteRow(
	DOCTYPE,
	'Email Template deleted successfully',
	'Error deleting email template'
)

const confirmDeletion = (row: SettingsListRow) => {
	createDialog({
		title: __('Delete {0}?').format(row.name),
		message: __(
			'This permanently deletes the email template and cannot be undone.'
		),
		size: 'sm',
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick({ close }: { close: () => void }) {
					removeTemplate(row).then(close)
				},
			},
		],
	})
}

/**
 * Duplicate, as a write rather than a prefilled form. The record page is opened
 * by name, and a name only exists once the record does, so the copy is inserted
 * straight away and edited by opening it.
 */

// `__newname` is what carries the name. Email Template autonames by Prompt, and
// that is the key Document.set_new_name() reads it from.
const duplicateTemplate = async (row: SettingsListRow) => {
	try {
		await call('frappe.client.insert', {
			doc: {
				doctype: DOCTYPE,
				__newname: `${row.name} - Copy`,
				subject: row.subject,
				use_html: row.use_html ? 1 : 0,
				response: row.response,
				response_html: row.response_html,
			},
		})
		toast.success(__('Email Template created successfully'))
		await reloadSettingsLists(DOCTYPE)
	} catch (err: any) {
		toast.error(
			cleanError(err.messages?.[0] || err) ||
				__('Error creating email template')
		)
	}
}

export const templateColumns: SettingsListColumn[] = [
	{
		key: 'name',
		get label() {
			return __('Template Name')
		},
		type: 'stacked',
		primary: (row) => row.name,
		secondary: (row) => row.subject,
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) => __('Actions for {0}').format(row.name),
		options: (row) => [
			{
				label: __('Duplicate'),
				icon: 'lucide-copy',
				onClick: () => duplicateTemplate(row),
			},
			{
				label: __('Delete'),
				icon: 'lucide-trash-2',
				onClick: () => confirmDeletion(row),
			},
		],
	},
]

/**
 * The whole page, list and record alike, is one component, so the settings tree
 * mounts it rather than assembling a list panel around a detail.
 */

// `component` is a getter and has to stay one. This module and the component
// import each other, so a plain `markRaw(EmailTemplates)` evaluates
// `markRaw(undefined)` on one import order and dies in a lazily loaded chunk.
export const emailTemplatesPage: CustomPage = {
	kind: 'custom',
	get component() {
		return markRaw(EmailTemplates)
	},
}
