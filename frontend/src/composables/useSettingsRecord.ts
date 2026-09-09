import {
	computed,
	type ComputedRef,
	type Ref,
	type WritableComputedRef,
} from 'vue'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import {
	useSettingsSource,
	type SettingsSourceHandle,
} from '@/composables/useSettingsSource'
import type { SettingsListRow } from '@/types'

export interface UseSettingsRecordOptions {
	doctype: string
	/** The record the panel opened, from the form's own `name` prop. */
	record: Ref<string | null> | ComputedRef<string | null>
	/**
	 * The fieldname whose value IS the document's name. A doctype that
	 * autonames `field:X` drops a set_value on X, so only a rename moves it.
	 */
	renameField?: string
	/**
	 * The Check field the header switch writes. Defaults to `enabled`; a
	 * payment's is `payment_received`.
	 */
	enabledField?: string
	/**
	 * Replaces the dirty computation, and is handed the source so it can read what
	 * the document resource thinks. A draft with defaults of its own has to ignore
	 * that answer, which for a new record is "holds anything at all".
	 */
	dirty?: (source: SettingsSourceHandle) => boolean
}

export interface SettingsRecordHandle {
	source: SettingsSourceHandle
	doc: ComputedRef<SettingsListRow | null>
	isNew: ComputedRef<boolean>
	isDirty: ComputedRef<boolean>
	loading: ComputedRef<boolean>
	/** The name the record answers to now, which a rename has moved. */
	name: ComputedRef<string | null>
	/**
	 * The record's own on/off state, as the header switch's boolean over the
	 * doctype's 0/1. Undefined while there is no document, which is what hides
	 * the switch for a record the header cannot yet report on.
	 */
	enabled: WritableComputedRef<boolean | undefined>
}

/**
 * The state every settings record form holds: the document, whether it is new,
 * whether it is dirty, the dirty guard's registration, and the header switch.
 * Nine forms had this written out by hand and identically.
 */

// Not here: the save, validation, seeding, or what happens after a write. The
// two endpoint-backed forms cannot use this at all, because one reads through
// a gated API and the other does not know its doctype until the server answers.
export function useSettingsRecord(
	options: UseSettingsRecordOptions
): SettingsRecordHandle {
	const source = useSettingsSource(
		{ doctype: options.doctype, record: 'route' },
		{ record: options.record, renameField: options.renameField }
	)

	const doc = computed(() => source.doc)
	const enabledField = options.enabledField ?? 'enabled'

	const isDirty = computed(() =>
		options.dirty ? Boolean(options.dirty(source)) : source.isDirty
	)

	// Refetch rather than reset field by field. The resource is module-cached by
	// [doctype, name], so without this the discarded edits stay in the document and
	// the next Save writes them.
	useDirtyGuard(
		() => isDirty.value,
		() => void source.reload()
	)

	const enabled = computed<boolean | undefined>({
		get: () => (doc.value ? Boolean(doc.value[enabledField]) : undefined),
		set: (value) => {
			if (doc.value) doc.value[enabledField] = value ? 1 : 0
		},
	})

	return {
		source,
		doc,
		isNew: computed(() => source.isNew),
		isDirty,
		loading: computed(() => source.loading),
		name: computed(() => source.name),
		enabled,
	}
}
