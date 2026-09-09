import { computed, reactive, shallowRef, watch, type Ref } from 'vue'
import { call, createDocumentResource } from 'frappe-ui'
import type { SettingsSource } from '@/types/settingsSchema'
import type { SettingsListRow } from '@/types/settingsList'

/** The record id a detail page uses for a row that is not on the server yet. */
export const NEW_RECORD = 'new'

const LMS_SETTINGS = 'LMS Settings'

/**
 * The slice of a frappe-ui document resource these pages touch. frappe-ui
 * ships `DocumentResource` only as an internal .d.ts and re-exports neither it
 * nor the path, so — as useSettingsListResource does for lists — it is
 * declared here.
 *
 * `isDirty` is the resource's own doc-vs-originalDoc value comparison, and
 * `save.submit()` sends only the changed fields and skips the round trip
 * entirely when there are none.
 */
export interface SettingsDocumentResource {
	/**
	 * The name the resource addresses, which every one of its requests is built
	 * from at send time. Writable, and that is what a rename needs it for.
	 */
	name: string
	doc: SettingsListRow | null
	/**
	 * The document as the resource last heard it from the server. It is the
	 * other half of `isDirty`, and the half a rename moves without it noticing.
	 */
	originalDoc?: SettingsListRow | null
	isDirty?: boolean
	get?: { loading: boolean }
	save: {
		submit: (values?: object, options?: object) => Promise<unknown>
		loading?: boolean
	}
	reload: () => Promise<unknown>
}

export interface UseSettingsSourceOptions {
	/**
	 * The record id for a `{ doctype, record: 'route' }` source, from the URL.
	 * {@link NEW_RECORD} yields a draft instead of a document.
	 */
	record?: Ref<string | null>
	/**
	 * A resource the caller already holds. Settings.vue loads LMS Settings once
	 * and hands it down, so a panel does not re-enter that document.
	 */
	resource?: SettingsDocumentResource
	/**
	 * The fieldname whose value IS the document's name, from the page's
	 * `renameField`. Editing it renames the record instead of writing a field.
	 */
	renameField?: string
}

export interface SettingsSourceHandle {
	/** Null while the document loads, and on a source with no record yet. */
	doc: SettingsListRow | null
	/**
	 * The name the record currently answers to, which after a rename is neither
	 * the one the URL carries nor the one the source declared. Exposed so the
	 * page above can rehash to it: without that the hash names a document the
	 * server has forgotten, and a browser refresh deep-links to nothing.
	 */
	name: string | null
	isDirty: boolean
	/** Writes the document, or inserts the draft when {@link isNew}. */
	save: () => Promise<unknown>
	reload: () => Promise<unknown>
	isNew: boolean
	loading: boolean
}

// createDocumentResource caches on [doctype, name] unconditionally: it ignores
// `options.cache` altogether (documentResource.js reads getCacheKey([doctype,
// name]) and never looks at the option), so two callers naming the same
// document get the same instance and neither can opt out. That is what makes
// LMS Settings safe to reach for from anywhere — it is one document, one dirty
// flag, one save. `cache` and `fields` are passed on the LMS Settings call
// only to keep it byte-identical to Settings.vue's and Preferences.vue's;
// dropping them would change nothing but would make three call sites that must
// resolve to one instance look like three different requests.
const documentResource = (
	doctype: string,
	name: string
): SettingsDocumentResource => {
	const options =
		doctype === LMS_SETTINGS
			? { doctype, name, fields: ['*'], cache: LMS_SETTINGS, auto: true }
			: { doctype, name, auto: true }
	return createDocumentResource(options) as unknown as SettingsDocumentResource
}

/**
 * Records a confirmed rename in the two copies the resource compares, because
 * nothing downstream will.
 *
 * getChangedFields() deletes `name` from every payload, so the rename IS the
 * write for the name and a save with nothing else to send resolves without a
 * request — leaving originalDoc naming a document the server has forgotten,
 * while isDirty compares the documents whole, name included. A page renaming
 * through `name` itself therefore read unsaved for good, with nothing left to
 * save. Only the name is touched: an edit still waiting to go out is none of
 * this function's business.
 *
 * isDirty is settled here rather than left to the resource, which recomputes it
 * only when `doc` mutates — and on such a page `doc` mutated before the save,
 * not after. A later edit re-runs the resource's own comparison over these
 * corrected copies and agrees.
 */
const settleRenamedName = (
	resource: SettingsDocumentResource,
	renamed: string
) => {
	if (resource.doc) resource.doc.name = renamed
	if (!resource.originalDoc) return
	resource.originalDoc.name = renamed
	resource.isDirty =
		JSON.stringify(resource.doc) !== JSON.stringify(resource.originalDoc)
}

// A draft is dirty once it holds anything worth writing. It has no originalDoc
// to compare against, so this is the closest honest answer to "is there
// something here that is not on the server".
const draftIsDirty = (draft: SettingsListRow): boolean =>
	Object.values(draft).some(
		(value) => value !== null && value !== undefined && value !== ''
	)

/**
 * Resolves a page's {@link SettingsSource} into something a fields panel can
 * read, write and save, whichever of the three kinds of source it is.
 */
export function useSettingsSource(
	source: SettingsSource,
	options: UseSettingsSourceOptions = {}
): SettingsSourceHandle {
	const doctype = 'doctype' in source ? source.doctype : LMS_SETTINGS

	const requested = computed<string | null>(() => {
		if ('doc' in source) return source.doc
		if ('name' in source) return source.name
		return options.record?.value ?? null
	})

	// The name a rename left the record answering to, which is neither the one
	// the URL carries nor the one the source declares — both still name a
	// document the server has forgotten. Held here so the open page stays on the
	// record the user just renamed.
	const renamedTo = shallowRef<string | null>(null)

	// Pointing the page at another record ends that hold.
	watch(requested, () => (renamedTo.value = null))

	const target = computed<string | null>(
		() => renamedTo.value ?? requested.value
	)

	const isNew = computed(() => target.value === NEW_RECORD)

	// A record that does not exist yet has no document to load, so it edits a
	// plain object. A fresh one each time, or the draft abandoned on the last
	// New would be waiting in the next one.
	const draft = shallowRef<SettingsListRow>(reactive({}))
	watch(isNew, (value) => {
		if (value) draft.value = reactive({})
	})

	// In a watcher rather than a computed: createDocumentResource registers in a
	// module-level cache and fires a request, which is not what a computed's
	// getter is allowed to do.
	const resource = shallowRef<SettingsDocumentResource | null>(null)
	watch(
		target,
		(name) => {
			if (options.resource) {
				resource.value = options.resource
				return
			}
			// A rename retargets the resource in place, so by the time this runs
			// the one already open IS the record the new name refers to. Entering
			// it again would fetch the document a second time and throw away the
			// copy the save just settled.
			if (resource.value?.name === name) return
			resource.value =
				!name || name === NEW_RECORD ? null : documentResource(doctype, name)
		},
		{ immediate: true }
	)

	// The name the user has edited the record's own name field to, or null when
	// there is nothing to rename. A blank is a half-typed field rather than a
	// name, and a value the record already answers to is not a change.
	const renameTarget = (doc: SettingsListRow | null): string | null => {
		const field = options.renameField
		if (!field || !doc || !(field in doc)) return null
		const value = doc[field]
		if (value === null || value === undefined || String(value).trim() === '')
			return null
		return String(value) === target.value ? null : String(value)
	}

	const save = async (): Promise<unknown> => {
		if (isNew.value)
			return call('frappe.client.insert', {
				doc: { doctype, ...draft.value },
			})
		const current = resource.value
		if (!current) return undefined

		const renamed = renameTarget(current.doc)
		if (renamed) {
			// Awaited, and first: a doctype named from a field ignores a set_value
			// on that field, so the rename is the only thing that moves the name —
			// and a rejected one must not be followed by the field write, or the
			// record ends up updated under a name the user did not mean to keep.
			await call('frappe.client.rename_doc', {
				doctype,
				old_name: target.value,
				new_name: renamed,
			})
			// The resource builds every request from its own `name` at send time,
			// so it is pointed at the new one before the fields go out. Without
			// this the write — and every later reload — addresses a document that
			// no longer exists.
			current.name = renamed
			renamedTo.value = renamed
			settleRenamedName(current, renamed)
		}
		return current.save.submit()
	}

	const reload = (): Promise<unknown> =>
		resource.value?.reload() ?? Promise.resolve()

	return reactive({
		doc: computed(() =>
			isNew.value ? draft.value : resource.value?.doc ?? null
		),
		name: target,
		isDirty: computed(() =>
			isNew.value ? draftIsDirty(draft.value) : Boolean(resource.value?.isDirty)
		),
		save,
		reload,
		isNew,
		loading: computed(() => Boolean(resource.value?.get?.loading)),
	}) as SettingsSourceHandle
}
