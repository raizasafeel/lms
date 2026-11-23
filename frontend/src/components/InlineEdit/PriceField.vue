<template>
	<div class="space-y-2">
		<div class="flex items-center justify-between gap-3">
			<span class="text-xl-semibold text-ink-gray-9">
				{{ headline }}
			</span>
			<Select
				:modelValue="paid ? 'paid' : 'free'"
				:options="options"
				variant="outline"
				:aria-label="label"
				class="w-28"
				@update:modelValue="(value) => emit('update:paid', value === 'paid')"
			/>
		</div>
		<PriceInput
			v-if="paid"
			:currency="currency"
			:amount="amount"
			:missing="missing"
			@update:currency="(value) => emit('update:currency', value)"
			@update:amount="(value) => emit('update:amount', value)"
		/>
	</div>
</template>

<script setup lang="ts">
import { Select } from 'frappe-ui'
import { computed } from 'vue'
import PriceInput from '@/components/InlineEdit/PriceInput.vue'
import { formatNumberIntoCurrency } from '@/utils'

/**
 * Free or paid, and the price when paid. `paid` is controlled, so a parent
 * can refuse the switch to paid by not applying it.
 */
const props = defineProps<{
	paid: boolean
	currency?: string | null
	amount?: number | null
	label: string
	missing?: boolean
}>()

const emit = defineEmits<{
	'update:paid': [value: boolean]
	'update:currency': [value: string]
	'update:amount': [value: number]
}>()

const options = [
	{ label: __('Free'), value: 'free' },
	{ label: __('Paid'), value: 'paid' },
]

const headline = computed<string>(() => {
	if (!props.paid) return __('Free')
	if (!props.amount || !props.currency) return __('Set a price')
	return formatNumberIntoCurrency(props.amount, props.currency)
})
</script>
