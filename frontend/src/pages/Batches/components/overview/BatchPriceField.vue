<template>
	<div class="flex items-center justify-between gap-2">
		<div v-if="doc.paid_batch" class="flex min-w-0 flex-1 items-center gap-1.5">
			<Link
				v-model="doc.currency"
				doctype="Currency"
				query="lms.lms.api.search_currencies"
				:filters="{ enabled: 1 }"
				:placeholder="__('Currency')"
				:aria-label="__('Currency')"
				variant="subtle"
				class="w-24 rounded-4"
				:class="ring('currency')"
			/>
			<FormControl
				:modelValue="doc.amount || ''"
				type="number"
				min="0"
				variant="subtle"
				:placeholder="__('Price')"
				:aria-label="__('Price')"
				class="min-w-0 flex-1 rounded-4"
				:class="ring('amount')"
				@update:modelValue="
					(value: string) => (doc.amount = Number(value) || 0)
				"
			/>
		</div>
		<span v-else class="flex-1 text-xl-semibold text-ink-gray-9">
			{{ __('Free') }}
		</span>
		<Dropdown :options="pricingOptions" align="end">
			<Button size="sm" variant="ghost">
				{{ doc.paid_batch ? __('Paid') : __('Set price') }}
				<template #suffix>
					<span class="lucide-chevron-down size-3.5" />
				</template>
			</Button>
		</Dropdown>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dropdown, FormControl } from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** Free or paid, and the price learners pay. */
const props = defineProps<{ doc: LMSBatch; form: BatchForm }>()

const ring = (key: string) =>
	props.form.isMissing(key) && 'bg-surface-red-1 ring-2 ring-outline-red-3'

const setPaid = (paid: boolean) => {
	;(props.doc as Record<string, unknown>).paid_batch = paid
}

const pricingOptions = computed(() => [
	{
		label: __('Free'),
		icon: props.doc.paid_batch ? undefined : 'lucide-check',
		onClick: () => setPaid(false),
	},
	{
		label: __('Paid'),
		icon: props.doc.paid_batch ? 'lucide-check' : undefined,
		onClick: () => setPaid(true),
	},
])
</script>
