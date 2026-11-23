import { call, createDocumentResource, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import {
	computed,
	inject,
	provide,
	reactive,
	ref,
	shallowRef,
	toRaw,
	watch,
} from 'vue'
import type { ComputedRef, InjectionKey, Ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import {
	joinFieldLabels,
	missingBatchFields,
	type MissingBatchField,
} from '@/utils/batchForm'
import { reportAutosaveError, submitResource } from '@/utils/resource'
import type { LMSBatch } from '@/types/lms/LMSBatch'
import type { BatchDetails, Resource } from '@/types'

const CHECKBOXES = [
	'published',
	'paid_batch',
	'allow_self_enrollment',
	'certification',
	'evaluation',
] as const

// Child tables other forms own: a whole-doc save must not overwrite them.
const UNSAVED_KEYS = [
	'modified',
	'courses',
	'assessment',
	'timetable',
	'timetable_legends',
]

export interface BatchMeta {
	description: string
	keywords: string
}

export interface BatchForm {
	doc: ComputedRef<LMSBatch | null>
	instructors: Ref<string[]>
	meta: BatchMeta
	isDirty: ComputedRef<boolean>
	showRequired: Ref<boolean>
	missingFields: ComputedRef<MissingBatchField[]>
	isMissing: (key: string) => boolean
	saveTooltip: ComputedRef<string>
	previewRequired: (on: boolean) => void
	submitBatch: () => void
}

export const BATCH_FORM: InjectionKey<BatchForm> = Symbol('batchForm')

/** The editing form, or null where the page is read-only. */
export function injectBatchForm(): BatchForm | null {
	return inject(BATCH_FORM, null)
}

const pad = (time: string): string => {
	const [hours, minutes] = (time || '').split(':')
	if (!minutes) return time
	return `${hours.padStart(2, '0')}:${minutes}`
}

function normalize(doc: LMSBatch): void {
	doc.start_time = pad(doc.start_time)
	doc.end_time = pad(doc.end_time)
	for (const key of CHECKBOXES) {
		;(doc as Record<string, unknown>)[key] = Boolean(doc[key])
	}
}

/**
 * The batch's editable state, shared by the Overview and Settings tabs.
 * Loads only while `enabled` is true, so learners never fetch the raw doc.
 */
export function useBatchForm(
	batchName: () => string,
	batch: Resource<BatchDetails | null>,
	enabled: () => boolean
): BatchForm {
	const resource = shallowRef(createBatchResource(batchName()))
	const doc = computed<LMSBatch | null>(() => resource.value.doc ?? null)
	const instructors = ref<string[]>([])
	const meta = reactive<BatchMeta>({ description: '', keywords: '' })
	const savedState = ref<string | null>(null)
	const savedMeta = ref<string>('')
	const showRequired = ref<boolean>(false)
	// A save with gaps keeps the rings until the gaps are filled.
	let requiredPinned = false

	function createBatchResource(name: string): Resource<LMSBatch | null> {
		return createDocumentResource({
			doctype: 'LMS Batch',
			name,
			auto: false,
		}) as Resource<LMSBatch | null>
	}

	const currentState = computed<string>(() =>
		JSON.stringify({ doc: doc.value, instructors: instructors.value })
	)
	const isMetaDirty = computed(() => JSON.stringify(meta) !== savedMeta.value)
	const isDirty = computed<boolean>(
		() =>
			savedState.value !== null &&
			(currentState.value !== savedState.value || isMetaDirty.value)
	)

	const missingFields = computed<MissingBatchField[]>(() =>
		missingBatchFields({ doc: doc.value, instructors: instructors.value })
	)
	const isMissing = (key: string): boolean =>
		showRequired.value && missingFields.value.some((f) => f.key === key)
	const missingLabels = () =>
		joinFieldLabels(missingFields.value.map((f) => f.label))

	const saveTooltip = computed<string>(() => {
		if (missingFields.value.length) {
			return __('Add {0} to save').format(missingLabels())
		}
		return isDirty.value ? __('Save') : __('No changes to save')
	})

	watch(missingFields, (missing) => {
		if (missing.length) return
		showRequired.value = false
		requiredPinned = false
	})

	/** Hovering Save rings the empty required fields. */
	function previewRequired(on: boolean): void {
		if (on) showRequired.value = missingFields.value.length > 0
		else if (!requiredPinned) showRequired.value = false
	}

	watch(batchName, (name) => {
		savedState.value = null
		resource.value = createBatchResource(name)
		if (enabled()) resource.value.reload()
	})

	watch(enabled, (on) => on && !doc.value && resource.value.reload(), {
		immediate: true,
	})

	// A save swaps in the server's doc too, so this also re-baselines after one.
	watch(
		doc,
		(loaded, previous) => {
			if (!loaded) return
			applyServerData(loaded)
			if (loaded.name !== previous?.name) loadMeta(loaded.name)
		},
		{ immediate: true }
	)

	function applyServerData(loaded: LMSBatch): void {
		normalize(loaded)
		instructors.value = (loaded.instructors || [])
			.map((row) => row.instructor)
			.filter(Boolean) as string[]
		savedState.value = currentState.value
	}

	function loadMeta(name: string): void {
		call('lms.lms.api.get_meta_info', { type: 'batches', route: name }).then(
			(rows: { key: string; value: string }[]) => {
				for (const row of rows || []) {
					if (row.key === 'description') meta.description = row.value
					if (row.key === 'keywords') meta.keywords = row.value
				}
				savedMeta.value = JSON.stringify(meta)
			}
		)
	}

	function saveMeta(name: string): void {
		call('lms.lms.api.update_meta_info', {
			meta_type: 'batches',
			route: name,
			meta_tags: [
				{ key: 'description', value: meta.description },
				{ key: 'keywords', value: meta.keywords },
			],
		}).catch((error: FrappeResourceError) => reportAutosaveError(error))
	}

	// A burst of edits collapses into one save. Gaps skip it quietly: the
	// "Not saved" badge stays and Save names what is missing.
	const autoSave = useDebounceFn((): void => {
		if (!isDirty.value || missingFields.value.length) return
		updateBatch({ silent: true })
	}, 1000)

	watch([currentState, isMetaDirty], () => isDirty.value && autoSave())

	function submitBatch(): void {
		if (missingFields.value.length) {
			showRequired.value = true
			requiredPinned = true
			toast.error(__('Add {0} before saving.').format(missingLabels()))
			return
		}
		updateBatch()
	}

	function payload(): Record<string, unknown> {
		const fields: Record<string, unknown> = { ...toRaw(doc.value) }
		for (const key of UNSAVED_KEYS) delete fields[key]
		fields.instructors = instructors.value.map((instructor) => ({ instructor }))
		return fields
	}

	function updateBatch(options: { silent?: boolean } = {}): void {
		if (!doc.value) return
		const metaChanged = isMetaDirty.value
		submitResource<LMSBatch>(resource.value.setValue, payload(), {
			onSuccess(saved) {
				if (metaChanged) {
					saveMeta(saved.name)
					savedMeta.value = JSON.stringify(meta)
				}
				if (!options.silent) toast.success(__('Batch saved'))
				batch.reload()
			},
			onError(error: FrappeResourceError) {
				reportAutosaveError(error, options.silent)
			},
		})
	}

	const form: BatchForm = {
		doc,
		instructors,
		meta,
		isDirty,
		showRequired,
		missingFields,
		isMissing,
		saveTooltip,
		previewRequired,
		submitBatch,
	}
	provide(BATCH_FORM, form)
	return form
}
