import type { Component } from 'vue'
import type { SettingsListColumn, SettingsListRow } from '@/types/settingsList'

/**
 * The settings tree, as data. Three kinds of page and nothing else: a page of
 * fields, a page of records, or a component. The kind is a discriminant, so a
 * renderer never branches on a panel's name.
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
	 * accepts, where hiding it would lose the very thing the page reports. The
	 * control is locked and the field commits nothing.
	 */
	disabled?: boolean
	/**
	 * Hides the field unless the document says otherwise. A hidden field is not
	 * written and not validated.
	 */
	showIf?: (doc: SettingsListRow) => boolean
}

/**
 * A value a control SHOWS while the document's own is empty, and nothing more.
 * Seeding it into the document would make the panel read dirty the instant it
 * opens. Not the checkbox `default`, which is written.
 */
interface DisplayFallback {
	displayFallback?: string
}

/**
 * Every control the settings pages use, as a discriminated union rather than a
 * bare string. FormControl falls through to a text input for anything it does
 * not recognise, so the union is what makes a mistyped `type` a compile error.
 */
export type SettingsField =
	| (FieldBase & {
			type: 'text' | 'email' | 'password' | 'number'
			/**
			 * A floor for a `number` field, enforced rather than suggested: the renderer
			 * puts a value below it back to the last good one and writes nothing.
			 * Declare it wherever the doctype's validate() would throw.
			 */
			min?: number
			/**
			 * Draw the control across the row with its label above, the way `textarea`
			 * and `richtext` are drawn. For a one-line value that is nonetheless long,
			 * such as an Email Template subject carrying Jinja placeholders.
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
				 * Passed to search_link as-is. A bench that also runs Frappe CRM gets an
				 * `enabled` field on Email Template, and search_widget then filters on it
				 * unless the caller declares filters, answering "No results".
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
	 * A body of prose, edited with a toolbar. Full-width, because the control
	 * column on the end of a row is 12rem wide and one line tall, and an editor
	 * with a fixed toolbar cannot live there.
	 */
	| (FieldBase & {
			type: 'richtext'
			/**
			 * Lines of content the control is sized for, exactly as `textarea` reads
			 * it. Two fields that swap for one another declare the same number, which
			 * is what makes the swap move nothing below them.
			 */
			rows?: number
	  })
	| (FieldBase & {
			type: 'upload'
			/**
			 * Opt in to a world-readable file. Everything else keeps frappe's private
			 * default; gateway KYC documents and QR codes reach these pages.
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
 * Which document a page reads and writes. Zoom and Google Meet have their own
 * doctypes, and a detail page's record comes from the URL.
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
	 * rather than on DetailPage because the panel rendering a fields page owns the
	 * header and is typed `page: FieldsPage`.
	 */
	enabledField?: string
	/**
	 * The fieldname whose value IS the document's name. Editing it renames the
	 * record, `rename_doc` first and the remaining fields after. Without this the
	 * field accepts an edit that is silently dropped.
	 */
	renameField?: string
	/**
	 * Ran once a manual save lands, holding what a hand-drawn form put after its
	 * own write: the success toast, the telemetry, and `back` to the list.
	 */
	onSaved?: (context: {
		created: boolean
		name: string | null
		back: () => void
	}) => void
}

export interface SettingsListSource {
	doctype: string
	fields: string[]
	filters?: Record<string, unknown>
	orderBy?: string
	/**
	 * Which columns the search box matches, as `like` orFilters. Without it the
	 * box renders and filters nothing. It cannot be derived from `fields`, which
	 * would `like`-match check and int columns too.
	 */
	searchFields?: string[]
	/** A whitelisted method returning rows, for catalogues with no doctype behind them. */
	method?: string
	/**
	 * The page size the rows arrive in, when it is not the panel's own. Load More
	 * is offered while a page comes back full, so a method that answers with a
	 * whole catalogue must declare a size no catalogue will reach.
	 */
	pageLength?: number
	/** Defaults to 'name'; catalogues keyed by something else say so. */
	rowKey?: string
}

/**
 * A record page behind a list row, reached by the back-button header. `title` is
 * called with an empty row for a create form and for a deep link to a record the
 * list has not fetched, so every implementation has to tolerate that.
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
 * a slug and back, and has no business knowing what a page renders.
 */
export interface SettingsRoutableItem {
	label: string
	/**
	 * The URL segment, declared rather than derived from the label. Several
	 * labels slugify badly, and renaming one would break every bookmark.
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
