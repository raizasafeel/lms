<template>
	<div class="space-y-4 rounded-6 border border-outline-gray-2 p-2 pb-4">
		<BatchImageField :doc="doc" />
		<div class="space-y-4 px-3">
			<BatchPriceField :doc="doc" :form="form" />
			<div>
				<Button variant="subtle" class="w-full" disabled>
					<template #prefix>
						<span
							class="size-4"
							:class="
								doc.paid_batch ? 'lucide-credit-card' : 'lucide-graduation-cap'
							"
						/>
					</template>
					{{ buttonLabel }}
				</Button>
				<p class="mt-1.5 text-center text-p-xs text-ink-gray-6">
					{{ buttonNote }}
				</p>
			</div>
			<div class="space-y-2.5 border-t border-outline-gray-1 pt-4">
				<div class="text-p-base-medium text-ink-gray-9">
					{{ __('This batch includes') }}
				</div>
				<BatchFactsEditor :doc="doc" :form="form" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import BatchFactsEditor from '@/pages/Batches/components/overview/BatchFactsEditor.vue'
import BatchImageField from '@/pages/Batches/components/overview/BatchImageField.vue'
import BatchPriceField from '@/pages/Batches/components/overview/BatchPriceField.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** The enrol card as instructors edit it: same layout learners see. */
const props = defineProps<{ doc: LMSBatch; form: BatchForm }>()

const isSelfEnroll = computed(
	() =>
		Boolean(props.doc.paid_batch) || Boolean(props.doc.allow_self_enrollment)
)

const buttonLabel = computed(() => {
	if (props.doc.paid_batch) return __('Register Now')
	if (props.doc.allow_self_enrollment) return __('Enroll Now')
	return __('Contact the Administrator to enroll for this batch')
})

const buttonNote = computed(() =>
	isSelfEnroll.value
		? __('Learners see this button.')
		: __(
				'Self enrollment is off in Settings, so learners see this message and you enroll them.'
		  )
)
</script>
