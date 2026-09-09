import type { Component } from 'vue'
import type { SettingsListColumn, SettingsListRow } from '@/types/settingsList'

/**
 * The settings tree, as data. Three kinds of page and nothing else: a page of
 * fields, a page of records, or — for the handful that are genuinely not either —
 * a component.
 *
 * The kind is a discriminant, so a renderer never branches on a panel's name.
 */

export interface SelectOption {
	label: string
	value: string
}

export type FieldOptions = string[] | SelectOption[]

interface FieldBase {
	/** Fieldname on the page's source document. */
	name: string
	label: string
	description?: string
	placeholder?: string
	reqd?: boolean
	/**
	 * Shown, and never written. For a value the document records rather than
	 * accepts — Transactions' member consent, Coupons' redemption count — where
	 * hiding it would lose the very thing the page is there to report. The
	 * control is locked and the field commits nothing.
	 */
	disabled?: boolean
	/**
	 * Hides the field unless the document says otherwise — Transactions' coupon
	 * block is the only caller. A hidden field is not written and not validated.
	 */
	showIf?: (doc: SettingsListRow) => boolean
}

/**
 * A value a control SHOWS while the document's own is empty, and nothing more.
 *
 * It is never written by being shown. Seeding it into the document instead
 * would make the document differ from `originalDoc`, so the resource reports
 * the panel dirty the instant it opens — and because `useAutosave`'s status
 * reports `dirty` ahead of `saved`, the header then reads "Not saved" before
 * anyone has touched it and never reaches "Saved" after a write either. The
 * document keeps its blank until the user picks something.
 *
 * Not the checkbox `default`, which is the opposite and IS written: a checkbox
 * Frappe returns as null renders off but saves nothing, so a `default: 1` field
 * would silently flip off the first time anything else on the page was saved.
 * A picker has no such trap — an unwritten blank stays blank.
 */
interface DisplayFallback {
	displayFallback?: string
}

/**
 * Every control the settings pages use, as a discriminated union rather than a
 * bare string. frappe-ui's FormControl falls through to `<TextInput :type>` for
 * anything it does not recognise, so a mistyped `type` would render a text input
 * instead of failing — the union is what makes that a compile error.
 */
export type SettingsField =
	| (FieldBase & {
			type: 'text' | 'email' | 'password' | 'number'
			/**
			 * A floor for a `number` field, enforced and not merely suggested: the
			 * renderer puts a value below it — or cleared, or non-numeric — back to
			 * the last good one when the field is left, and writes nothing. Declare
			 * it wherever the doctype's validate() would throw, since a rejected
			 * autosave has no Save button to retry from.
			 */
			min?: number
			/**
			 * Draw the control across the row with its label above, the way
			 * `textarea` and `richtext` are drawn, instead of in the 12rem column
			 * on the end edge.
			 *
			 * For a one-line value that is nonetheless long: an Email Template's
			 * subject is a sentence carrying Jinja placeholders, and 12rem showed
			 * the user "Your batch {{ batch }} star" and stopped. Not a textarea
			 * instead — a control that accepts a newline would be lying about a
			 * field the server stores as one line.
			 */
			fullWidth?: boolean
	  })
	| (FieldBase & { type: 'textarea'; rows?: number })
	| (FieldBase & DisplayFallback & { type: 'select'; options: FieldOptions })
	| (FieldBase & { type: 'combobox'; options: FieldOptions })
	| (FieldBase &
			DisplayFallback & {
				type: 'link'
				/** A function when the target depends on another field, as LMS Payment's does. */
				doctype: string | ((doc: SettingsListRow) => string)
				/**
				 * Passed to search_link as-is. A bench that also runs Frappe CRM gets
				 * an `enabled` Check custom field on Email Template, and frappe's
				 * search_widget appends `enabled = 1` for any doctype carrying one
				 * unless the caller sends `include_disabled` — so a template picker
				 * that declares no filters answers "No results" over a full table.
				 */
				filters?: Record<string, unknown>
				onCreate?: (value: string, close: () => void) => void
			})
	| (FieldBase & { type: 'checkbox'; default?: 0 | 1 })
	| (FieldBase & { type: 'date' })
	| (FieldBase & {
			type: 'code'
			mode: 'htmlmixed' | 'javascript'
			rows?: number
	  })
	/**
	 * A body of prose, edited with a toolbar.
	 *
	 * Full-width — label above, control below — for the same reason `code` and
	 * `textarea` are: the control column on the end of a row is 12rem wide and
	 * one line tall, which is where a name or a number goes. An editor carrying
	 * a fixed toolbar and several lines of content cannot live there, and
	 * squeezing it in would make the row taller than the panel's other rows put
	 * together.
	 */
	| (FieldBase & {
			type: 'richtext'
			/**
			 * Lines of content the control is sized for, exactly as `textarea`
			 * reads it. Two fields that swap for one another — Email Template's
			 * HTML body and its rich one — declare the same number, which is what
			 * makes the swap move nothing below them.
			 */
			rows?: number
	  })
	| (FieldBase & {
			type: 'upload'
			/**
			 * Opt in to a world-readable file. Everything else keeps frappe's private
			 * default — gateway KYC documents and merchant QR codes reach these pages.
			 */
			public?: boolean
			size?: 'lg'
	  })

export type SettingsFieldType = SettingsField['type']

export interface FieldsSection {
	label?: string
	fields: SettingsField[]
}

/**
 * Which document a page reads and writes. Not every panel writes LMS Settings:
 * Zoom and Google Meet have their own doctypes, and a detail page's record comes
 * from the URL.
 */
export type SettingsSource =
	| { doc: 'LMS Settings' }
	| { doctype: string; name: string }
	| { doctype: string; record: 'route' }

/** Runtime field metadata, e.g. LMS Payment's server-declared `reqd` flags. */
export type FieldMeta = Record<string, { reqd?: boolean | 0 | 1 }>

export interface FieldsPage {
	kind: 'fields'
	source: SettingsSource
	/** Autosave on commit, or an explicit Save button. */
	save: 'auto' | 'manual'
	sections: FieldsSection[]
	/**
	 * Supplies `reqd` at runtime where the server owns it. A field's own `reqd`
	 * stands where no meta is returned for it.
	 */
	meta?: () => Promise<FieldMeta>
	/**
	 * Hoists a toggle for this fieldname into the page header. It lives here
	 * rather than on DetailPage because the panel that renders a fields page owns
	 * the header, and it is typed `page: FieldsPage` — a detail-only key would be
	 * unreachable from there without a cast.
	 */
	enabledField?: string
	/**
	 * The fieldname whose value IS the document's name — 'account_name' for Zoom
	 * and Google Meet, whose doctypes autoname from it, and 'name' itself for an
	 * Email Template.
	 *
	 * Editing it renames the record: `rename_doc` first, then the remaining
	 * fields. Nothing else moves a document's name, so without this the field
	 * accepts an edit that is silently dropped and the record keeps the name it
	 * was created with — which is exactly what happened when the three forms
	 * that used to do this by hand became config.
	 */
	renameField?: string
}

export interface SettingsListSource {
	doctype: string
	fields: string[]
	filters?: Record<string, unknown>
	orderBy?: string
	/**
	 * Which columns the search box matches, as `like` orFilters. Without it the
	 * box renders and filters nothing — `useSettingsListResource` builds the
	 * search from this list alone. It cannot be derived from `fields`: that
	 * would `like`-match check and int columns too.
	 */
	searchFields?: string[]
	/** A whitelisted method returning rows, for catalogues with no doctype behind them. */
	method?: string
	/**
	 * The page size the rows arrive in, when it is not the panel's own.
	 *
	 * Load More is offered while a page comes back full, so a method that
	 * answers with a whole catalogue in one call must declare a size no
	 * catalogue will reach — otherwise the fourteenth row makes the list offer
	 * a page that does not exist, and fetching it appends the same rows again.
	 */
	pageLength?: number
	/** Defaults to 'name'; catalogues keyed by something else say so. */
	rowKey?: string
}

/**
 * A record page behind a list row, reached by the back-button header.
 *
 * `title` is called with an empty row for a create form, and for a deep link to
 * a record the list has not fetched yet — every implementation has to tolerate
 * that rather than assume a loaded row.
 */
export type DetailPage =
	| (FieldsPage & { title: (row: SettingsListRow) => string })
	| { kind: 'custom'; component: Component }

export interface ListPage {
	kind: 'list'
	resource: SettingsListSource
	columns: SettingsListColumn[]
	searchable?: boolean
	empty?: { name: string; icon?: string }
	create?: { label?: string; detail: DetailPage }
	rowDetail?: DetailPage
}

export interface CustomPage {
	kind: 'custom'
	component: Component
}

export type SettingsPage = FieldsPage | ListPage | CustomPage

/**
 * The slice of an item the URL layer needs. `useSettingsHash` resolves a hash to
 * a slug and back; it has no business knowing what a page renders, and taking
 * the narrow type is what lets its tests declare two-line fixtures.
 */
export interface SettingsRoutableItem {
	label: string
	/**
	 * The URL segment. Declared, never derived from the label: 'Payment >
	 * Configuration' and 'Communication > Templates' both slugify badly, and
	 * renaming a label would silently break every bookmark.
	 */
	slug: string
	/**
	 * Opt in to '#settings/<slug>/<record>'. Without it a second hash segment is
	 * stripped, so a page with no detail view cannot grow a phantom record id.
	 */
	records?: boolean
}

export interface SettingsRoutableGroup {
	label: string
	hideLabel?: boolean
	items: SettingsRoutableItem[]
}

export interface SettingsItem extends SettingsRoutableItem {
	icon: string
	condition?: () => boolean
	page: SettingsPage
}

export interface SettingsGroup extends SettingsRoutableGroup {
	items: SettingsItem[]
}
