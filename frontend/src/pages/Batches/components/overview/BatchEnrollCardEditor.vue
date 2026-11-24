<template>
	<div class="space-y-3 rounded-6 border border-outline-gray-2 p-4">
		<div class="flex items-center gap-2">
			<Select
				:modelValue="doc.paid_batch ? 'paid' : 'free'"
				:options="priceOptions"
				variant="ghost"
				:aria-label="__('Batch price')"
				class="w-24 shrink-0"
				@update:modelValue="(value) => setPaid(value === 'paid')"
			/>
			<PriceInput
				v-if="doc.paid_batch"
				:currency="doc.currency"
				:amount="doc.amount"
				:missing="form.isMissing('currency') || form.isMissing('amount')"
				class="min-w-0 flex-1"
				@update:currency="(value) => (doc.currency = value)"
				@update:amount="(value) => (doc.amount = value)"
			/>
		</div>
		<BatchFactsEditor :doc="doc" :form="form" :studentCount="studentCount" />
		<div class="space-y-2">
			<VideoPreview
				:video-link="doc.video_link"
				:fallback-image="doc.meta_image"
				class="rounded-5"
			/>
			<Button variant="ghost" @click="showVideoDialog = true">
				<template #prefix>
					<span class="lucide-video size-4" />
				</template>
				{{ doc.video_link ? __('Change video') : __('Add preview video') }}
			</Button>
		</div>
		<VideoLinkDialog
			v-model:open="showVideoDialog"
			:modelValue="doc.video_link"
			@update:modelValue="(link) => (doc.video_link = link || '')"
		/>
		<div class="pt-1">
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
			<p v-if="buttonNote" class="mt-1.5 text-center text-p-xs text-ink-gray-6">
				{{ buttonNote }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Select } from 'frappe-ui'
import PriceInput from '@/components/InlineEdit/PriceInput.vue'
import VideoLinkDialog from '@/components/InlineEdit/VideoLinkDialog.vue'
import VideoPreview from '@/components/VideoPreview.vue'
import BatchFactsEditor from '@/pages/Batches/components/overview/BatchFactsEditor.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'
import { formatNumberIntoCurrency } from '@/utils'

/** The enrol card as instructors edit it: same layout learners see. */
const props = defineProps<{
	doc: LMSBatch
	form: BatchForm
	studentCount?: number
}>()

const showVideoDialog = ref(false)

const priceOptions = [
	{ label: __('Free'), value: 'free' },
	{ label: __('Paid'), value: 'paid' },
]

// The form keeps checkboxes as booleans, so the dirty check sees no change
// after switching back.
const setPaid = (paid: boolean): void => {
	;(props.doc as Record<string, unknown>).paid_batch = paid
}

const isSelfEnroll = computed(
	() =>
		Boolean(props.doc.paid_batch) || Boolean(props.doc.allow_self_enrollment)
)

const buttonLabel = computed<string>(() => {
	if (props.doc.paid_batch) {
		const price = formatNumberIntoCurrency(props.doc.amount, props.doc.currency)
		return price ? __('Enroll for {0}').format(price) : __('Enroll')
	}
	if (props.doc.allow_self_enrollment) return __('Enroll')
	return __('Contact the Administrator to enroll for this batch')
})

const buttonNote = computed(() =>
	isSelfEnroll.value
		? ''
		: __(
				'Self enrollment is off in Settings, so learners see this message and you enroll them.'
		  )
)
</script>
