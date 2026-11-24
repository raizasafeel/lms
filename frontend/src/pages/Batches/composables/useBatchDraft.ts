import { call, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import { computed, provide, reactive, ref, toRaw } from 'vue'
import { cleanError } from '@/utils'
import { missingBatchFields } from '@/utils/batchForm'
import { sanitizeStringFields } from '@/utils/sanitizeOnWrite'
import {
	BATCH_FORM,
	useRequiredRings,
	type BatchForm,
	type BatchMeta,
} from '@/pages/Batches/composables/useBatchForm'
import type { BatchAssessment } from '@/pages/Batches/components/overview/assessmentTypes'
import type { LMSBatch } from '@/types/lms/LMSBatch'

export interface BatchDraft extends BatchForm {
	draft: NonNullable<BatchForm['draft']>
}

function blankBatch(): Partial<LMSBatch> {
	return {
		title: '',
		description: '',
		batch_details: '',
		category: undefined,
		start_date: undefined,
		end_date: undefined,
		start_time: '',
		end_time: '',
		timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
		medium: 'Online',
		seat_count: 0,
		published: 0,
		paid_batch: 0,
		allow_self_enrollment: 0,
		certification: 0,
		evaluation: 0,
	}
}

/** The insert payload: the batch with its instructors, courses and assessments. */
export function batchInsertDoc(
	doc: Partial<LMSBatch>,
	instructors: string[],
	courses: string[],
	assessments: BatchAssessment[]
): Record<string, unknown> {
	const fields = { ...toRaw(doc) } as Record<string, unknown>
	sanitizeStringFields(fields)
	return {
		...fields,
		doctype: 'LMS Batch',
		instructors: instructors.map((instructor) => ({ instructor })),
		courses: courses.map((course) => ({ course })),
		assessment: assessments.map((row) => ({
			assessment_type: row.assessment_type,
			assessment_name: row.assessment_name,
		})),
	}
}

/**
 * A batch that exists only on the page until its first save. It offers the
 * same form the batch overview edits, so the overview renders it unchanged.
 */
export function useBatchDraft(onCreated: (name: string) => void): BatchDraft {
	const doc = reactive(blankBatch()) as LMSBatch
	const instructors = ref<string[]>([])
	const meta = reactive<BatchMeta>({ description: '', keywords: '' })
	const courses = ref<string[]>([])
	const assessments = ref<BatchAssessment[]>([])
	const saving = ref<boolean>(false)

	const missingFields = computed(() =>
		missingBatchFields({ doc, instructors: instructors.value })
	)
	const rings = useRequiredRings(missingFields)

	async function create(): Promise<void> {
		const batch = await call('frappe.client.insert', {
			doc: batchInsertDoc(
				doc,
				instructors.value,
				courses.value,
				assessments.value
			),
		})
		if (meta.description || meta.keywords) {
			call('lms.lms.api.update_meta_info', {
				meta_type: 'batches',
				route: batch.name,
				meta_tags: [
					{ key: 'description', value: meta.description },
					{ key: 'keywords', value: meta.keywords },
				],
			})
		}
		onCreated(batch.name)
	}

	function submitBatch(): void {
		if (saving.value || !rings.checkRequired()) return
		saving.value = true
		create()
			.catch((error: FrappeResourceError) => {
				toast.error(
					cleanError(error.messages?.[0]) || __('Could not create the batch')
				)
			})
			.finally(() => {
				saving.value = false
			})
	}

	const form: BatchDraft = {
		doc: computed(() => doc),
		instructors,
		meta,
		isDirty: computed(() => true),
		showRequired: rings.showRequired,
		missingFields,
		isMissing: rings.isMissing,
		saveTooltip: computed(() =>
			missingFields.value.length
				? __('Add {0} to save').format(rings.missingLabels())
				: __('Save')
		),
		previewRequired: rings.previewRequired,
		submitBatch,
		isSaving: computed(() => saving.value),
		draft: { courses, assessments },
	}
	provide(BATCH_FORM, form)
	return form
}
